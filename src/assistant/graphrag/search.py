"""Два режима поиска по графу. Требования FR-4, FR-5 и FR-10."""

import itertools
import json

import networkx as nx

from assistant.infra.grounding import code_type, find_codes, find_names
from assistant.infra.llm import LLMClient
from assistant.infra.schemas import MAP_SCHEMA, Answer, KnowledgeBase


def _find_names_fuzzy(question: str, vocab: dict[str, list[str]]) -> list[tuple[str, str]]:
    """Находит словарные названия в вопросе с учётом русских падежей (стем-префикс)."""
    low = question.lower()
    found: list[tuple[str, str]] = []
    for kind, names in vocab.items():
        for name in names:
            words = [w for w in name.lower().split() if len(w) >= 3]
            if not words:
                continue
            if all((w[: max(4, len(w) - 2)] if len(w) >= 5 else w) in low for w in words):
                found.append((kind, name))
    return found


def _add_replacement_chains_and_details(
    graph: nx.DiGraph,
    collected_edges: set[tuple[str, str]],
) -> None:
    """Добавляет все ветки цепочек REPLACED_BY от найденных деталей и их связи SUPPLIED_BY / IS_A."""
    queue = [
        node for edge in collected_edges for node in edge if graph.nodes[node].get("type") == "Part"
    ]
    all_parts: set[str] = set(queue)
    while queue:
        curr = queue.pop(0)
        for succ in graph.successors(curr):
            if graph.edges[curr, succ].get("type") == "REPLACED_BY":
                collected_edges.add((curr, succ))
                if succ not in all_parts:
                    all_parts.add(succ)
                    queue.append(succ)

    for part in all_parts:
        for succ in graph.successors(part):
            if graph.edges[part, succ].get("type") in ("SUPPLIED_BY", "IS_A"):
                collected_edges.add((part, succ))


def local_search(question: str, kb: KnowledgeBase, llm: LLMClient) -> Answer:
    """Отвечает на вопрос о конкретных сущностях по фактам из графа.

    Опорные сущности ищутся без модели: коды через `find_codes`, названия через `find_names`.
    При двух и более опорных сущностях берутся факты на путях длиной до трёх связей между ними
    и цепочки `REPLACED_BY` от деталей на этих путях. При одной берётся окрестность на глубину
    до двух связей. Модель получает пронумерованный список фактов и отвечает только по нему.
    Если в вопросе есть код, которого нет в графе, или фактов нет, возвращается
    `Answer(..., refused=True)` без вызова модели.
    """
    codes = find_codes(question)
    for code in codes:
        node_id = f"{code_type(code)}:{code}"
        if node_id not in kb.graph:
            return Answer(text="В базе знаний не найдено.", sources=[], facts=[], refused=True)

    anchors: set[str] = set()
    for code in codes:
        node_id = f"{code_type(code)}:{code}"
        if node_id in kb.graph:
            anchors.add(node_id)

    matched_names = find_names(question, kb.vocabulary)
    for kind, name in matched_names:
        node_id = f"{kind}:{name}"
        if node_id in kb.graph:
            anchors.add(node_id)

    for kind, name in _find_names_fuzzy(question, kb.vocabulary):
        node_id = f"{kind}:{name}"
        if node_id in kb.graph:
            anchors.add(node_id)

    if not anchors:
        return Answer(text="В базе знаний не найдено.", sources=[], facts=[], refused=True)

    undirected = kb.graph.to_undirected(as_view=True)
    collected_edges: set[tuple[str, str]] = set()
    distances: dict[str, int] = {}

    if len(anchors) >= 2:
        anchor_list = sorted(anchors)
        for i in range(len(anchor_list)):
            for j in range(i + 1, len(anchor_list)):
                u_node = anchor_list[i]
                v_node = anchor_list[j]
                if nx.has_path(undirected, u_node, v_node):
                    for path in nx.all_simple_paths(undirected, source=u_node, target=v_node, cutoff=3):
                        for a, b in itertools.pairwise(path):
                            if kb.graph.has_edge(a, b):
                                collected_edges.add((a, b))
                            if kb.graph.has_edge(b, a):
                                collected_edges.add((b, a))

        _add_replacement_chains_and_details(kb.graph, collected_edges)
        rel_prio = {
            "REPLACED_BY": 0,
            "SUPPLIED_BY": 1,
            "FIXED_BY": 2,
            "INDICATES": 3,
            "FAILED": 4,
            "IS_A": 5,
            "BELONGS_TO": 6,
            "HAS_PART": 7,
        }
        ordered_edges = sorted(
            collected_edges,
            key=lambda edge: (rel_prio.get(kb.graph.edges[edge[0], edge[1]].get("type", ""), 9), edge[0], edge[1]),
        )
    else:
        anchor = next(iter(anchors))
        distances = nx.single_source_shortest_path_length(undirected, anchor, cutoff=2)
        for a, b in kb.graph.edges:
            if a in distances and b in distances and min(distances[a], distances[b]) <= 1:
                collected_edges.add((a, b))

        _add_replacement_chains_and_details(kb.graph, collected_edges)
        ordered_edges = sorted(
            collected_edges,
            key=lambda edge: (
                0 if anchor in edge else 1,
                min(distances.get(edge[0], 99), distances.get(edge[1], 99)),
                edge[0],
                edge[1],
            ),
        )

    if not ordered_edges:
        return Answer(text="В базе знаний не найдено.", sources=[], facts=[], refused=True)

    facts: list[str] = []
    doc_sources: set[str] = set()

    for a, b in ordered_edges:
        data = kb.graph.edges[a, b]
        rel_type = data.get("type", "")
        weight = data.get("weight", 1)
        a_name = kb.graph.nodes[a].get("name", a)
        b_name = kb.graph.nodes[b].get("name", b)
        if rel_type == "FAILED":
            facts.append(f"{a_name} -{rel_type}-> {b_name} (отказов: {weight})")
        else:
            facts.append(f"{a_name} -{rel_type}-> {b_name}")
        for s in data.get("sources", []):
            doc_sources.add(s.split("#")[0])

    facts_lines: list[str] = []
    total_chars = 0
    for i, fact in enumerate(facts):
        line = f"{i + 1}. {fact}"
        if total_chars + len(line) + 1 > 8000:
            break
        facts_lines.append(line)
        total_chars += len(line) + 1

    facts_text = "\n".join(facts_lines)

    messages = [
        {
            "role": "system",
            "content": (
                "Ты ассистент сервисной службы «ПолярТех». Отвечай на вопрос кратко, точно и строго по "
                "приведённым фактам. Сохраняй точные коды (SP-xxx, P-xxxx, AR-xxx, E-xx) и названия.\n"
                "Правила:\n"
                "- Если спрашивается о регламенте (SP-xxx), укажи точный код регламента из связи FIXED_BY.\n"
                "- Если спрашивается, какую деталь заказать / ставится / поставщика детали и у исходной "
                "детали есть цепочка замен REPLACED_BY, обязательно дойди до ПОСЛЕДНЕЙ актуальной детали "
                "в этой цепочке (и её поставщика SUPPLIED_BY).\n"
                "- Если спрашивается, в каких моделях стояла снятая деталь, перечисли все модели со связью HAS_PART.\n"
                "- Не выдумывай факты вне приведённого списка и не указывай цены, остатки или количество штук "
                "(руб, ₽, шт), которых нет в фактах базы знаний."
            ),
        },
        {"role": "user", "content": f"Вопрос: {question}\n\nФакты из базы знаний:\n{facts_text}"},
    ]

    response = llm.chat(messages)
    answer_text = response.content.strip()
    allowed_codes = set(find_codes(question)) | set(find_codes(facts_text))
    invented_codes = [c for c in find_codes(answer_text) if c not in allowed_codes]
    if invented_codes:
        retry_messages = [
            *messages,
            response.as_message(),
            {
                "role": "user",
                "content": (
                    f"Коды {', '.join(invented_codes)} отсутствуют в приведённых фактах. "
                    "Перепиши ответ кратко и точно, используя ТОЛЬКО коды из списка фактов и вопроса."
                ),
            },
        ]
        answer_text = llm.chat(retry_messages).content.strip()

    return Answer(
        text=answer_text,
        sources=sorted(doc_sources),
        facts=facts,
        refused=False,
    )


def _community_product_lines(
    nodes: list[str],
    graph: nx.DiGraph,
    model_to_line: dict[str, str],
) -> set[str]:
    """Определяет, к каким линейкам оборудования относится сообщество."""
    lines: set[str] = set()
    for node in nodes:
        if node not in graph:
            continue
        if graph.nodes[node].get("type") == "ProductLine":
            lines.add(graph.nodes[node].get("name", node))
        elif node in model_to_line:
            lines.add(model_to_line[node])
    return lines


def global_search(question: str, kb: KnowledgeBase, llm: LLMClient) -> Answer:
    """Отвечает на обзорный вопрос по сводкам сообществ в два шага.

    Шаг map: для каждой сводки модель даёт частичный ответ и оценку полезности от 0 до 10.
    Шаг reduce: частичные ответы с оценкой выше 0 объединяются в итоговый ответ.
    Если таких ответов нет, возвращается `Answer(..., refused=True)`.
    """
    codes = find_codes(question)
    if any(f"{code_type(c)}:{c}" not in kb.graph for c in codes):
        return Answer(text="В базе знаний не найдено.", sources=[], facts=[], refused=True)

    asked_lines: set[str] = {
        name
        for kind, name in (find_names(question, kb.vocabulary) + _find_names_fuzzy(question, kb.vocabulary))
        if kind == "ProductLine"
    }
    model_to_line: dict[str, str] = {}
    for u, v, data in kb.graph.edges(data=True):
        if data.get("type") == "BELONGS_TO":
            model_to_line[u] = kb.graph.nodes[v].get("name", v)

    scored_answers: list[tuple[int, str]] = []
    all_sources: set[str] = set()

    for comm in kb.communities:
        messages = [
            {
                "role": "system",
                "content": (
                    "Ты аналитик «ПолярТех». Ответь на вопрос строго по сводке сообщества и оцени полезность "
                    "от 0 до 10 по схеме MAP_SCHEMA.\n"
                    "Ставь score=0, если:\n"
                    "- в сводке нет прямого ответа на вопрос;\n"
                    "- в вопросе указана конкретная линейка оборудования, а сводка относится к другой линейке;\n"
                    "- вопрос о цене, остатке на складе или о коде, которого нет в сводке."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Вопрос: {question}\n\nСводка сообщества:\n{comm.summary}\n\n"
                    "Верни JSON с полями answer и score."
                ),
            },
        ]
        try:
            resp = llm.chat(messages, json_schema=MAP_SCHEMA)
            data = json.loads(resp.content)
            if isinstance(data, dict) and "score" in data and "answer" in data:
                score = int(data["score"])
                ans_text = str(data["answer"]).strip()
                if score > 0 and ans_text:
                    comm_lines = _community_product_lines(comm.nodes, kb.graph, model_to_line)
                    mentions_asked = any(line.lower() in comm.summary.lower() for line in asked_lines)
                    if asked_lines and not (comm_lines & asked_lines) and not mentions_asked:
                        continue
                    scored_answers.append((score, ans_text))
                    for node in comm.nodes:
                        for s in kb.graph.nodes[node].get("sources", []):
                            all_sources.add(s.split("#")[0])
        except Exception:
            continue

    if not scored_answers:
        return Answer(text="В базе знаний не найдено.", sources=[], facts=[], refused=True)

    scored_answers.sort(key=lambda item: -item[0])
    partial_answers = [ans for _, ans in scored_answers]
    partials_text = "\n".join(f"- [оценка {score}] {ans}" for score, ans in scored_answers)

    reduce_messages = [
        {
            "role": "system",
            "content": (
                "Ты ассистент сервисной службы «ПолярТех». Объедини полезные частичные ответы в краткий "
                "и точный итоговый ответ. Сохраняй точные коды моделей и деталей (P-xxxx, BZ-xxx), "
                "названия узлов и линеек. Не выдумывай факты и коды."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Вопрос: {question}\n\n"
                f"Полезные частичные ответы:\n{partials_text}\n\n"
                "Сформируй итоговый ответ."
            ),
        },
    ]
    reduce_resp = llm.chat(reduce_messages)
    final_text = reduce_resp.content.strip()

    valid_graph_codes = {
        kb.graph.nodes[n].get("name", "")
        for n in kb.graph.nodes
        if kb.graph.nodes[n].get("type") in ("Model", "Part", "ErrorCode", "Procedure")
    }
    allowed_codes = (set(find_codes(partials_text)) & valid_graph_codes) | set(find_codes(question))
    invented_codes = [c for c in find_codes(final_text) if c not in allowed_codes]
    if invented_codes:
        retry_reduce = [
            *reduce_messages,
            reduce_resp.as_message(),
            {
                "role": "user",
                "content": (
                    f"Коды {', '.join(invented_codes)} не подтверждены базой знаний. "
                    "Перепиши итоговый ответ без этих кодов, опираясь строго на подтверждённые частичные ответы."
                ),
            },
        ]
        final_text = llm.chat(retry_reduce).content.strip()

    return Answer(
        text=final_text,
        sources=sorted(all_sources),
        facts=partial_answers,
        refused=False,
    )
