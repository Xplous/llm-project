"""Сообщества графа и их сводки. Требование FR-3."""

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


def summarize_community(community: Community, graph: nx.DiGraph, llm: LLMClient) -> str:
    """Сводка сообщества не длиннее 150 слов: какие сущности входят, как связаны, что встречается чаще.

    Все числа считает код по весам рёбер и передаёт модели готовыми. Модель их только формулирует.
    """
    community_nodes = set(community.nodes)

    edge_descriptions: list[str] = []
    for u, v, data in graph.edges(data=True):
        if u in community_nodes and v in community_nodes:
            rel_type = data.get("type", "")
            weight = data.get("weight", 1)
            u_name = graph.nodes[u].get("name", u)
            v_name = graph.nodes[v].get("name", v)
            edge_descriptions.append(f"{u_name} -[{rel_type}]-> {v_name} (зафиксировано: {weight})")

    if not edge_descriptions:
        for u, v, data in graph.edges(data=True):
            if u in community_nodes or v in community_nodes:
                rel_type = data.get("type", "")
                weight = data.get("weight", 1)
                u_name = graph.nodes[u].get("name", u)
                v_name = graph.nodes[v].get("name", v)
                edge_descriptions.append(f"{u_name} -[{rel_type}]-> {v_name} (зафиксировано: {weight})")

    facts_text = "\n".join(edge_descriptions[:50])

    prompt = (
        f"Составь краткую сводку сообщества графа знаний (строго до 150 слов).\n"
        f"Опиши, какие ключевые сущности входят в сообщество, как они связаны и какие проблемы/узлы "
        f"встречаются чаще всего согласно готовым подсчётам:\n\n"
        f"Факты и подсчёты:\n{facts_text}\n"
    )

    messages = [
        {"role": "system", "content": "Ты эксперт по сервисному обслуживанию оборудования «ПолярТех»."},
        {"role": "user", "content": prompt},
    ]

    response = llm.chat(messages, max_tokens=300)
    words = response.content.strip().split()
    if len(words) > 150:
        return " ".join(words[:150])
    return response.content.strip()
