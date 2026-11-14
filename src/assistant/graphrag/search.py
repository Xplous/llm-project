"""Два режима поиска по графу. Требования FR-4, FR-5 и FR-10."""

import itertools
import json

import networkx as nx

from assistant.infra.grounding import code_type, find_codes, find_names
from assistant.infra.llm import LLMClient
from assistant.infra.schemas import MAP_SCHEMA, Answer, KnowledgeBase


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

    for kind, name in find_names(question, kb.vocabulary):
        node_id = f"{kind}:{name}"
        if node_id in kb.graph:
            anchors.add(node_id)

    if not anchors:
        return Answer(text="В базе знаний не найдено.", sources=[], facts=[], refused=True)

    undirected = kb.graph.to_undirected(as_view=True)
    collected_edges: set[tuple[str, str]] = set()

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

        part_nodes = {
            node for edge in collected_edges for node in edge if kb.graph.nodes[node].get("type") == "Part"
        }
        for part in part_nodes:
            curr = part
            visited_parts = {curr}
            while True:
                next_part = None
                for succ in kb.graph.successors(curr):
                    if kb.graph.edges[curr, succ].get("type") == "REPLACED_BY":
                        collected_edges.add((curr, succ))
                        if succ not in visited_parts:
                            next_part = succ
                            visited_parts.add(succ)
                        break
                if next_part is None:
                    break
                curr = next_part
    else:
        anchor = next(iter(anchors))
        lengths = nx.single_source_shortest_path_length(undirected, anchor, cutoff=2)
        neighborhood = set(lengths.keys())
        for a, b in kb.graph.edges:
            if a in neighborhood and b in neighborhood:
                collected_edges.add((a, b))

    if not collected_edges:
        return Answer(text="В базе знаний не найдено.", sources=[], facts=[], refused=True)

    facts: list[str] = []
    doc_sources: set[str] = set()

    for a, b in sorted(collected_edges):
        data = kb.graph.edges[a, b]
        rel_type = data.get("type", "")
        a_name = kb.graph.nodes[a].get("name", a)
        b_name = kb.graph.nodes[b].get("name", b)
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
                "Ты ассистент сервисной службы «ПолярТех». Отвечай на вопрос строго по предоставленным фактам "
                "из базы знаний. Если в фактах есть замена детали (REPLACED_BY), обязательно называй в ответе "
                "актуальную финальную деталь цепочки замен. Не выдумывай информацию."
            ),
        },
        {"role": "user", "content": f"Вопрос: {question}\n\nФакты из базы знаний:\n{facts_text}"},
    ]

    response = llm.chat(messages)
    return Answer(
        text=response.content.strip(),
        sources=sorted(doc_sources),
        facts=facts,
        refused=False,
    )


def global_search(question: str, kb: KnowledgeBase, llm: LLMClient) -> Answer:
    """Отвечает на обзорный вопрос по сводкам сообществ в два шага.

    Шаг map: для каждой сводки модель даёт частичный ответ и оценку полезности от 0 до 10.
    Шаг reduce: частичные ответы с оценкой выше 0 объединяются в итоговый ответ.
    Если таких ответов нет, возвращается `Answer(..., refused=True)`.
    """
    partial_answers: list[str] = []
    all_sources: set[str] = set()

    for comm in kb.communities:
        messages = [
            {
                "role": "system",
                "content": "Ты эксперт по сервисному обслуживанию «ПолярТех». Оцени полезность сводки сообщества.",
            },
            {
                "role": "user",
                "content": (
                    f"Вопрос: {question}\n\nСводка сообщества:\n{comm.summary}\n\n"
                    f"Ответь на вопрос по этой сводке и оцени полезность ответа от 0 до 10 по схеме MAP_SCHEMA."
                ),
            },
        ]
        try:
            resp = llm.chat(messages, json_schema=MAP_SCHEMA)
            data = json.loads(resp.content)
            if isinstance(data, dict) and "score" in data and "answer" in data:
                score = int(data["score"])
                if score > 0 and data["answer"].strip():
                    partial_answers.append(data["answer"].strip())
                    for node in comm.nodes:
                        for s in kb.graph.nodes[node].get("sources", []):
                            all_sources.add(s.split("#")[0])
        except Exception:
            continue

    if not partial_answers:
        return Answer(text="В базе знаний не найдено.", sources=[], facts=[], refused=True)

    partials_text = "\n".join(f"- {ans}" for ans in partial_answers)
    reduce_messages = [
        {
            "role": "system",
            "content": (
                "Ты ассистент сервисной службы «ПолярТех». Сформируй итоговый ответ на основе "
                "полезных частичных ответов по сводкам."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Вопрос: {question}\n\n"
                f"Полезные частичные ответы:\n{partials_text}\n\n"
                f"Сформируй итоговый ответ."
            ),
        },
    ]
    reduce_resp = llm.chat(reduce_messages)
    return Answer(
        text=reduce_resp.content.strip(),
        sources=sorted(all_sources),
        facts=partial_answers,
        refused=False,
    )
