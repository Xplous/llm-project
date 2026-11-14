"""Сборка графа знаний из результатов извлечения. Требование FR-2."""

import networkx as nx

from assistant.infra.schemas import ExtractionResult


def build_graph(results: list[ExtractionResult]) -> nx.DiGraph:
    """Объединяет результаты по всем чанкам в один направленный граф.

    Узел: идентификатор `Entity.node_id`, атрибуты `type`, `name`, `sources` (список chunk_id).
    Ребро: атрибуты `type`, `weight` (число разных чанков, где связь найдена), `sources`.
    Связи, не соответствующие схеме (`Relation.matches_schema`), отбрасываются. Если между двумя
    деталями есть `REPLACED_BY` в обе стороны, остаётся связь с большим весом, при равенстве
    отбрасываются обе. Число таких конфликтов записывается в `graph.graph["conflicts"]`.
    """
    graph = nx.DiGraph(conflicts=0)

    for result in results:
        chunk_id = result.chunk_id
        for entity in result.entities:
            node_id = entity.node_id
            if node_id not in graph:
                graph.add_node(node_id, type=entity.type, name=entity.name, sources=[])
            if chunk_id not in graph.nodes[node_id]["sources"]:
                graph.nodes[node_id]["sources"].append(chunk_id)

    edges_data: dict[tuple[str, str], dict] = {}

    for result in results:
        chunk_id = result.chunk_id
        for relation in result.relations:
            if not relation.matches_schema():
                continue

            u = relation.subject.node_id
            v = relation.object.node_id

            if u not in graph:
                graph.add_node(u, type=relation.subject.type, name=relation.subject.name, sources=[])
            if v not in graph:
                graph.add_node(v, type=relation.object.type, name=relation.object.name, sources=[])

            if (u, v) not in edges_data:
                edges_data[(u, v)] = {"type": relation.type, "sources": set()}
            edges_data[(u, v)]["sources"].add(chunk_id)

    for (u, v), data in edges_data.items():
        sources = sorted(data["sources"])
        graph.add_edge(u, v, type=data["type"], weight=len(sources), sources=sources)

    for node in graph.nodes:
        graph.nodes[node]["sources"] = sorted(set(graph.nodes[node]["sources"]))

    conflicts = 0
    resolved_pairs: set[tuple[str, str]] = set()

    for u, v in list(graph.edges):
        if not graph.has_edge(u, v):
            continue
        if graph.edges[u, v].get("type") == "REPLACED_BY":
            if graph.has_edge(v, u) and graph.edges[v, u].get("type") == "REPLACED_BY":
                pair_key = (min(u, v), max(u, v))
                if pair_key in resolved_pairs:
                    continue
                resolved_pairs.add(pair_key)
                conflicts += 1

                weight_uv = graph.edges[u, v]["weight"]
                weight_vu = graph.edges[v, u]["weight"]

                if weight_uv > weight_vu:
                    graph.remove_edge(v, u)
                elif weight_vu > weight_uv:
                    graph.remove_edge(u, v)
                else:
                    graph.remove_edge(u, v)
                    graph.remove_edge(v, u)

    graph.graph["conflicts"] = conflicts
    return graph
