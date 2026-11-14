"""Детальные тесты функционала Эпика 2: Сообщества (FR-3), локальный (FR-4) и глобальный поиск (FR-5, FR-10)."""

import networkx as nx
import pytest

from assistant.graphrag.communities import detect_communities, summarize_community
from assistant.graphrag.search import global_search, local_search
from assistant.infra.schemas import Community, KnowledgeBase
from assistant.infra.testing import FakeLLM


@pytest.fixture()
def sample_kb() -> KnowledgeBase:
    """Создаёт тестовый граф с несколькими моделями, ошибками, цепочкой замен и компонентами."""
    graph = nx.DiGraph(conflicts=0)

    # Узлы и связи
    # AR-210 -> P-1042 -> P-1042B -> P-1042C (двухшаговая замена)
    # E-17 -> пусковое реле <- P-1042
    edges = [
        ("Model:AR-210", "BELONGS_TO", "ProductLine:Арктика", 1, ["manual_AR-210.md#0"]),
        ("Model:AR-210", "HAS_PART", "Part:P-1042", 1, ["manual_AR-210.md#0"]),
        ("Part:P-1042", "IS_A", "Component:пусковое реле", 1, ["manual_AR-210.md#0"]),
        ("ErrorCode:E-17", "INDICATES", "Component:пусковое реле", 2, ["manual_AR-210.md#1"]),
        ("ErrorCode:E-17", "FIXED_BY", "Procedure:SP-104", 1, ["procedure_SP-104.md#0"]),
        ("Part:P-1042", "REPLACED_BY", "Part:P-1042B", 2, ["bulletin_SB-2025-01.md#0"]),
        ("Part:P-1042B", "REPLACED_BY", "Part:P-1042C", 1, ["bulletin_SB-2025-02.md#0"]),
        ("Part:P-1042C", "SUPPLIED_BY", "Supplier:ХолодКомплект", 1, ["bulletin_SB-2025-02.md#0"]),
        ("Model:AR-210", "FAILED", "Component:пусковое реле", 42, ["report_R-2025-001.md#0"]),
        # Другая изолированная модель BZ-110
        ("Model:BZ-110", "BELONGS_TO", "ProductLine:Бриз", 1, ["manual_BZ-110.md#0"]),
        ("Model:BZ-110", "HAS_PART", "Part:P-2001", 1, ["manual_BZ-110.md#0"]),
        ("Part:P-2001", "IS_A", "Component:компрессор", 1, ["manual_BZ-110.md#0"]),
    ]

    for s, rel, t, w, sources in edges:
        for node in (s, t):
            if node not in graph:
                ntype, name = node.split(":", 1)
                graph.add_node(node, type=ntype, name=name, sources=[])
            graph.nodes[node]["sources"] = sorted(set(graph.nodes[node]["sources"]) | set(sources))
        graph.add_edge(s, t, type=rel, weight=w, sources=sources)

    vocab = {
        "ProductLine": ["Арктика", "Бриз"],
        "Component": ["пусковое реле", "компрессор"],
        "Supplier": ["ХолодКомплект"],
    }

    nodes = sorted(graph.nodes)
    communities = [
        Community(0, [n for n in nodes if "AR-210" in n or "P-1042" in n or "E-17" in n], "Сводка линейки Арктика."),
        Community(1, [n for n in nodes if "BZ-110" in n or "P-2001" in n], "Сводка линейки Бриз."),
    ]

    return KnowledgeBase(graph, communities, vocab)


# --- ТЕСТЫ СООБЩЕСТВ (FR-3) ---


def test_detect_communities_включает_каждый_узел_ровно_в_одно_сообщество(sample_kb):
    """Проверяет, что каждый узел графа входит ровно в 1 сообщество и нумерация идет с 0."""
    communities = detect_communities(sample_kb.graph)
    all_members = [node for c in communities for node in c.nodes]

    assert sorted(all_members) == sorted(sample_kb.graph.nodes)
    assert len(all_members) == len(set(all_members))  # нет дублирования
    assert [c.community_id for c in communities] == list(range(len(communities)))


def test_detect_communities_разделяет_несвязные_компоненты_графа():
    """Проверяет, что несвязные кластеры гарантированно попадают в разные сообщества."""
    g = nx.DiGraph()
    # Кластер 1
    g.add_edge("Part:P-1", "Part:P-2", type="REPLACED_BY", weight=1, sources=[])
    # Кластер 2 (полностью изолирован)
    g.add_edge("Part:P-99", "Part:P-100", type="REPLACED_BY", weight=1, sources=[])

    for n in g.nodes:
        g.nodes[n]["type"] = "Part"
        g.nodes[n]["name"] = n.split(":")[1]

    communities = detect_communities(g)
    assert len(communities) == 2
    groups = [sorted(c.nodes) for c in communities]
    assert ["Part:P-1", "Part:P-2"] in groups
    assert ["Part:P-100", "Part:P-99"] in groups


def test_detect_communities_дает_воспроизводимое_разбиение_при_фиксированном_seed(sample_kb):
    """Проверяет детерминированность разбиения алгоритма Лувена."""
    run1 = [sorted(c.nodes) for c in detect_communities(sample_kb.graph)]
    run2 = [sorted(c.nodes) for c in detect_communities(sample_kb.graph)]
    assert run1 == run2


def test_summarize_community_передает_веса_связей_отказов_в_промпт_модели(sample_kb):
    """Проверяет передачу готовых статистических весов (42 отказа) в промпт модели."""
    comm = Community(0, sorted(sample_kb.graph.nodes))
    llm = FakeLLM(["Сводка сообщества: частые отказы пускового реле."])

    summarize_community(comm, sample_kb.graph, llm)

    prompt = " ".join(str(m["content"]) for m in llm.requests[0]["messages"])
    assert "42" in prompt
    assert "пусковое реле" in prompt


def test_summarize_community_строго_ограничивает_сводку_150_словами(sample_kb):
    """Проверяет, что многословный ответ модели принудительно обрезается до 150 слов."""
    comm = Community(0, sorted(sample_kb.graph.nodes))
    long_text = "слово " * 350
    llm = FakeLLM([long_text])

    summary = summarize_community(comm, sample_kb.graph, llm)

    assert 0 < len(summary.split()) <= 150


# --- ТЕСТЫ ЛОКАЛЬНОГО ПОИСКА (FR-4, FR-10) ---


def test_local_search_строит_многошаговую_цепочку_замен_детали(sample_kb):
    """Проверяет поиск путей между E-17 и AR-210 с добавлением цепочки замен P-1042 -> P-1042B -> P-1042C."""
    llm = FakeLLM(["Актуальная деталь – P-1042C."])
    answer = local_search("Какую деталь заказать при ошибке E-17 на модели AR-210?", sample_kb, llm)

    prompt = " ".join(str(m["content"]) for m in llm.requests[0]["messages"])
    # Проверяем, что в промпт попали все шаги замен
    assert "P-1042" in prompt
    assert "P-1042B" in prompt
    assert "P-1042C" in prompt
    assert "P-2001" not in prompt  # деталь другой модели не должна попасть

    assert not answer.refused
    assert "bulletin_SB-2025-02.md" in answer.sources
    assert all("#" not in s for s in answer.sources)


def test_local_search_читает_окрестность_радиуса_два_для_одной_опорной_сущности(sample_kb):
    """Проверяет сбор фактов в радиусе 2 шагов при единственной опорной сущности."""
    llm = FakeLLM(["Поставщик – ХолодКомплект."])
    answer = local_search("Кто поставляет деталь P-1042B?", sample_kb, llm)

    prompt = " ".join(str(m["content"]) for m in llm.requests[0]["messages"])
    assert "P-1042C" in prompt
    assert "ХолодКомплект" in prompt
    assert not answer.refused


def test_local_search_немедленно_отказывает_без_вызова_модели_если_код_отсутствует_в_графе(sample_kb):
    """Проверяет быстрый отказ без обращения к LLM при неизвестном коде оборудования или ошибки."""
    llm = FakeLLM([])
    for q in ["Что делать при ошибке E-99 на AR-210?", "Какая деталь в модели AR-999?"]:
        ans = local_search(q, sample_kb, llm)
        assert ans.refused
        assert ans.text == "В базе знаний не найдено."
        assert len(llm.requests) == 0


def test_local_search_немедленно_отказывает_если_в_вопросе_нет_опорных_сущностей(sample_kb):
    """Проверяет быстрый отказ без вызова LLM, если вопрос не содержит ни кодов, ни названий из словаря."""
    llm = FakeLLM([])
    ans = local_search("Как поживает сервисная служба сегодня?", sample_kb, llm)
    assert ans.refused
    assert len(llm.requests) == 0


# --- ТЕСТЫ ГЛОБАЛЬНОГО ПОИСКА (FR-5, FR-10) ---


def test_global_search_выполняет_map_по_сводкам_и_reduce_полезных_ответов(sample_kb):
    """Проверяет двухшаговый Map-Reduce поиск с отсевом ответов со score=0."""
    llm = FakeLLM(
        [
            '{"answer": "В Арктике чаще всего выходит из строя пусковое реле.", "score": 9}',
            '{"answer": "В Бризе отказов не зафиксировано.", "score": 0}',
            "Итоговый ответ: в линейке Арктика чаще всего отказывает пусковое реле.",
        ]
    )

    ans = global_search("Какие проблемы чаще всего возникают в оборудовании?", sample_kb, llm)

    assert len(llm.requests) == 3
    # Проверяем, что map-вызовы использовали схему
    assert llm.requests[0]["json_schema"] is not None
    assert llm.requests[1]["json_schema"] is not None

    # Reduce-вызов не содержит ответ с оценкой 0
    reduce_prompt = " ".join(str(m["content"]) for m in llm.requests[2]["messages"])
    assert "В Арктике чаще всего выходит из строя пусковое реле." in reduce_prompt
    assert "В Бризе отказов не зафиксировано." not in reduce_prompt

    assert not ans.refused
    assert ans.text == "Итоговый ответ: в линейке Арктика чаще всего отказывает пусковое реле."


def test_global_search_отказывает_если_все_сводки_получили_оценку_ноль(sample_kb):
    """Проверяет отказ, если ни одна сводка сообщества не дала полезной информации."""
    llm = FakeLLM(
        [
            '{"answer": "нет данных", "score": 0}',
            '{"answer": "нет данных", "score": 0}',
        ]
    )

    ans = global_search("Какая средняя зарплата инженера?", sample_kb, llm)
    assert ans.refused
    assert ans.text == "В базе знаний не найдено."
    assert len(llm.requests) == 2  # reduce не вызывался


def test_global_search_устойчив_к_некорректному_json_на_шаге_map(sample_kb):
    """Проверяет, что битый JSON на этапе map одной сводки не прерывает работу с остальными."""
    llm = FakeLLM(
        [
            "битый ответ не json",
            '{"answer": "В Арктике зафиксированы отказы реле.", "score": 7}',
            "В линейке Арктика зафиксированы отказы реле.",
        ]
    )

    ans = global_search("Какие поломки известны?", sample_kb, llm)
    assert not ans.refused
    assert ans.text == "В линейке Арктика зафиксированы отказы реле."
    assert len(llm.requests) == 3
