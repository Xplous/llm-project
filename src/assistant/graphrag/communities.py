"""Сообщества графа и их сводки. Требование FR-3."""

from collections import Counter

import networkx as nx

from assistant.infra.llm import LLMClient
from assistant.infra.schemas import Community

SEED = 7


def detect_communities(graph: nx.DiGraph) -> list[Community]:
    """Разбивает узлы на сообщества алгоритмом Лувена с фиксированным `seed`.

    Каждый узел входит ровно в одно сообщество. Поле `summary` здесь остаётся пустым.
    """
    undirected = nx.Graph()
    for node, data in graph.nodes(data=True):
        undirected.add_node(node, **data)

    for u, v, data in graph.edges(data=True):
        weight = data.get("weight", 1)
        if undirected.has_edge(u, v):
            undirected[u][v]["weight"] += weight
        else:
            undirected.add_edge(u, v, weight=weight)

    raw_communities = nx.community.louvain_communities(undirected, weight="weight", seed=SEED)

    sorted_groups = sorted([sorted(group) for group in raw_communities], key=lambda nodes: nodes[0] if nodes else "")

    return [Community(community_id=i, nodes=nodes, summary="") for i, nodes in enumerate(sorted_groups)]


def _replacement_chain(part_node: str, graph: nx.DiGraph) -> list[str]:
    """Возвращает цепочку замен начиная с `part_node`."""
    chain = [graph.nodes[part_node].get("name", part_node)]
    curr = part_node
    visited = {curr}
    while True:
        next_node = next(
            (r for r in graph.successors(curr) if graph.edges[curr, r].get("type") == "REPLACED_BY"),
            None,
        )
        if next_node is None or next_node in visited:
            break
        visited.add(next_node)
        chain.append(graph.nodes[next_node].get("name", next_node))
        curr = next_node
    return chain


def _compute_line_stats(community_nodes: set[str], graph: nx.DiGraph) -> list[str]:
    """Считает детерминированную статистику отказов и снятых деталей по связанным линейкам и моделям."""
    model_to_line: dict[str, str] = {}
    for u, v, data in graph.edges(data=True):
        if data.get("type") == "BELONGS_TO":
            model_to_line[u] = graph.nodes[v].get("name", v)

    relevant_lines: set[str] = set()
    for node in community_nodes:
        if node not in graph:
            continue
        if graph.nodes[node].get("type") == "ProductLine":
            relevant_lines.add(graph.nodes[node].get("name", node))
        elif node in model_to_line:
            relevant_lines.add(model_to_line[node])

    stats_lines: list[str] = []
    for line_name in sorted(relevant_lines):
        models_in_line = sorted(m for m, pl in model_to_line.items() if pl == line_name)
        if not models_in_line:
            continue

        comp_failures: Counter[str] = Counter()
        model_failures: Counter[str] = Counter()
        disc_models: dict[str, list[str]] = {}
        disc_chains: dict[str, list[str]] = {}

        for model_id in models_in_line:
            model_name = graph.nodes[model_id].get("name", model_id)
            for succ in graph.successors(model_id):
                edge = graph.edges[model_id, succ]
                etype = edge.get("type")
                weight = edge.get("weight", 1)
                if etype == "FAILED":
                    comp_name = graph.nodes[succ].get("name", succ)
                    comp_failures[comp_name] += weight
                    model_failures[model_name] += weight
                elif etype == "HAS_PART":
                    chain = _replacement_chain(succ, graph)
                    if len(chain) > 1:
                        part_name = chain[0]
                        disc_models.setdefault(part_name, []).append(model_name)
                        disc_chains[part_name] = chain

        models_names = ", ".join(graph.nodes[m].get("name", m) for m in models_in_line)
        stats_lines.append(f"Линейка «{line_name}» (модели: {models_names}):")
        if comp_failures:
            ranked_comps = comp_failures.most_common()
            top_comp, top_cnt = ranked_comps[0]
            comp_str = ", ".join(f"{name} ({cnt})" for name, cnt in ranked_comps)
            stats_lines.append(f"  Чаще всего отказывает узел: {top_comp} ({top_cnt}); все отказы узлов: {comp_str}.")
        if model_failures:
            ranked_mods = model_failures.most_common()
            top_mod, top_mcnt = ranked_mods[0]
            mod_str = ", ".join(f"{name} ({cnt})" for name, cnt in ranked_mods)
            mod_line = f"  Больше всего отказов у модели: {top_mod} ({top_mcnt}); отказы по моделям: {mod_str}."
            stats_lines.append(mod_line)
        if disc_models:
            parts_desc = [
                f"{p} (модели {', '.join(sorted(disc_models[p]))}; замена: {' -> '.join(disc_chains[p])})"
                for p in sorted(disc_models)
            ]
            stats_lines.append(f"  Снятые с производства детали линейки: {'; '.join(parts_desc)}.")

    return stats_lines


def summarize_community(community: Community, graph: nx.DiGraph, llm: LLMClient) -> str:
    """Сводка сообщества не длиннее 150 слов: какие сущности входят, как связаны, что встречается чаще.

    Все числа считает код по весам рёбер и передаёт модели готовыми. Модель их только формулирует.
    """
    community_nodes = set(community.nodes)

    node_labels = [
        f"{graph.nodes[n].get('type', '')}:{graph.nodes[n].get('name', n)}"
        for n in sorted(community_nodes)
        if n in graph
    ]

    incident_edges: list[tuple[int, str]] = []
    for u, v, data in graph.edges(data=True):
        if u in community_nodes or v in community_nodes:
            rel_type = data.get("type", "")
            weight = data.get("weight", 1)
            u_name = graph.nodes[u].get("name", u)
            v_name = graph.nodes[v].get("name", v)
            desc = f"{u_name} -[{rel_type}]-> {v_name} (вес: {weight})"
            incident_edges.append((weight, desc))

    incident_edges.sort(key=lambda item: (-item[0], item[1]))
    edge_lines = [desc for _, desc in incident_edges[:50]]
    stats_lines = _compute_line_stats(community_nodes, graph)

    sections = [f"Узлы сообщества ({len(node_labels)}): {', '.join(node_labels)}."]
    if stats_lines:
        sections.append("Готовые подсчёты по линейкам и моделям:\n" + "\n".join(stats_lines))
    if edge_lines:
        sections.append("Связи сообщества:\n" + "\n".join(edge_lines))
    else:
        sections.append("Связи сообщества: отсутствуют (0 рёбер).")

    facts_text = "\n\n".join(sections)

    if stats_lines:
        extra_rules = (
            "- Обязательно включи в сводку все данные из блока «Готовые подсчёты по линейкам и моделям»: "
            "название линейки, узел-лидер по отказам (с числом), модель-лидер по отказам (с числом) "
            "и все снятые с производства детали линейки (с их заменами).\n"
            "- Не трать объём сводки на перечисление всех штатных деталей моделей.\n"
        )
    else:
        extra_rules = (
            "- Это тематическое сообщество без линейки оборудования: опиши узлы, коды ошибок, "
            "регламенты, поставщиков и замены деталей.\n"
            "- НЕ указывай «линейку», «узел-лидер по отказам» и «модель-лидер по отказам».\n"
        )

    prompt = (
        "Составь краткую сводку сообщества графа знаний (строго до 130 слов).\n"
        "Опиши: какие сущности входят в сообщество, как они связаны, что встречается чаще всего.\n"
        "ОБЯЗАТЕЛЬНЫЕ ПРАВИЛА:\n"
        "- Используй ТОЛЬКО приведённые ниже факты, коды, названия и числа; не выдумывай проценты.\n"
        f"{extra_rules}\n"
        f"{facts_text}"
    )

    messages = [
        {
            "role": "system",
            "content": "Ты технический аналитик «ПолярТех». Формулируешь точные сводки строго по фактам.",
        },
        {"role": "user", "content": prompt},
    ]

    response = llm.chat(messages, max_tokens=400)
    words = response.content.strip().split()
    if len(words) > 150:
        return " ".join(words[:150])
    return response.content.strip()
