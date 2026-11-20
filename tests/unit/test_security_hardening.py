"""Регрессионные тесты закрытия уязвимостей из red-team аудита."""

import json

import networkx as nx

from assistant.agent.agent import run_agent
from assistant.graphrag.communities import summarize_community
from assistant.graphrag.extraction import extract_chunk
from assistant.graphrag.graph_builder import build_graph
from assistant.graphrag.search import global_search, local_search
from assistant.infra.llm import LLMResponse, ToolCall
from assistant.infra.schemas import Chunk, Community, Entity, ExtractionResult, KnowledgeBase, Relation


class _FakeLLM:
    def __init__(self, responses: list[str | ToolCall]):
        self._responses = list(responses)

    def chat(self, messages, **_kwargs) -> LLMResponse:
        item = self._responses.pop(0)
        if isinstance(item, ToolCall):
            return LLMResponse(content="", tool_calls=[item])
        return LLMResponse(content=item, tool_calls=[])


def test_extraction_rejects_hallucinated_non_code_entity_not_in_chunk():
    """Не-кодовые сущности (поставщик/узел), отсутствующие в чанке, должны отбрасываться."""
    chunk = Chunk("doc.md#0", "doc.md", "Модель AR-210 входит в линейку Арктика.")
    payload = {
        "entities": [
            {"type": "Model", "name": "AR-210"},
            {"type": "ProductLine", "name": "Арктика"},
            {"type": "Supplier", "name": "ХолодКомплект"},
        ],
        "relations": [
            {
                "subject_type": "Model",
                "subject": "AR-210",
                "type": "BELONGS_TO",
                "object_type": "ProductLine",
                "object": "Арктика",
            }
        ],
    }
    res = extract_chunk(chunk, _FakeLLM([json.dumps(payload, ensure_ascii=False)]))
    assert {e.node_id for e in res.entities} == {"Model:AR-210", "ProductLine:Арктика"}
    assert res.dropped == 1


def test_graph_builder_breaks_three_node_replaced_by_cycle():
    """Цикл REPLACED_BY длины 3 должен разрываться с увеличением счётчика conflicts."""
    p1 = Entity("Part", "P-1001")
    p2 = Entity("Part", "P-1002")
    p3 = Entity("Part", "P-1003")
    results = [
        ExtractionResult("c1", "d1", [p1, p2], [Relation(p1, "REPLACED_BY", p2)]),
        ExtractionResult("c2", "d2", [p1, p2], [Relation(p1, "REPLACED_BY", p2)]),
        ExtractionResult("c3", "d3", [p2, p3], [Relation(p2, "REPLACED_BY", p3)]),
        ExtractionResult("c4", "d4", [p2, p3], [Relation(p2, "REPLACED_BY", p3)]),
        ExtractionResult("c5", "d5", [p3, p1], [Relation(p3, "REPLACED_BY", p1)]),
    ]
    g = build_graph(results)
    assert g.graph["conflicts"] == 1
    assert not g.has_edge("Part:P-1003", "Part:P-1001")
    assert g.has_edge("Part:P-1001", "Part:P-1002")
    assert g.has_edge("Part:P-1002", "Part:P-1003")


def test_local_search_matches_inflected_russian_component_name():
    """Косвенный падеж («пускового реле») не должен давать ложный отказ."""
    g = nx.DiGraph()
    g.add_node("ErrorCode:E-17", type="ErrorCode", name="E-17", sources=["p.md#0"])
    g.add_node("Component:пусковое реле", type="Component", name="пусковое реле", sources=["p.md#0"])
    g.add_node("Procedure:SP-104", type="Procedure", name="SP-104", sources=["p.md#0"])
    g.add_edge("ErrorCode:E-17", "Component:пусковое реле", type="INDICATES", weight=1, sources=["p.md#0"])
    g.add_edge("ErrorCode:E-17", "Procedure:SP-104", type="FIXED_BY", weight=1, sources=["p.md#0"])
    kb = KnowledgeBase(graph=g, communities=[], vocabulary={"Component": ["пусковое реле"]})

    ans = local_search("Какой регламент для пускового реле?", kb, _FakeLLM(["Регламент SP-104."]))
    assert not ans.refused
    assert "SP-104" in ans.text


def test_agent_validates_warehouse_before_confirm_false_gate():
    """Несуществующий склад не должен попадать в pending_action при confirm=False."""
    bad_order = ToolCall(
        id="c1",
        name="create_service_order",
        arguments={"part_id": "P-1042B", "warehouse": "Екатеринбург", "qty": 2, "model": "AR-210"},
    )
    llm = _FakeLLM([bad_order, "Склад Екатеринбург не поддерживается."])
    res = run_agent(
        "Оформи заказ: 2 штуки P-1042B для AR-210, склад Екатеринбург.",
        llm,
        {"create_service_order": lambda **kw: kw},
        confirm=False,
    )
    assert not res.needs_confirmation
    assert res.pending_action is None
    assert res.steps and res.steps[0].error is not None


def test_agent_does_not_whitelist_hallucinated_code_from_search_answer():
    """Выдуманный код в answer от search_knowledge (отсутствующий в facts) не должен проходить проверку."""
    search_call = ToolCall(id="c1", name="search_knowledge", arguments={"question": "ошибка E-14 на AR-320"})
    llm = _FakeLLM(
        [
            search_call,
            "Регламент SP-205, деталь P-1118B.",
            "Деталь P-1118B.",
        ]
    )
    tools = {
        "search_knowledge": lambda **_: {
            "answer": "Деталь P-1118B, регламент SP-205.",
            "facts": ["AR-320 -HAS_PART-> P-1118B"],
            "sources": ["manual_AR-320.md"],
            "refused": False,
        }
    }
    res = run_agent("Ошибка E-14 на AR-320?", llm, tools)
    assert "SP-205" not in res.answer
    assert "P-1118B" in res.answer


def test_summarize_community_prepends_deterministic_stats_within_150_words():
    """Статистика отказов и снятых деталей должна детерминированно попадать в начало сводки <= 150 слов."""
    g = nx.DiGraph()
    g.add_node("ProductLine:Гольфстрим", type="ProductLine", name="Гольфстрим", sources=[])
    g.add_node("Model:GS-100", type="Model", name="GS-100", sources=[])
    g.add_node("Component:пусковое реле", type="Component", name="пусковое реле", sources=[])
    g.add_node("Part:P-3011", type="Part", name="P-3011", sources=[])
    g.add_node("Part:P-3011B", type="Part", name="P-3011B", sources=[])
    g.add_edge("Model:GS-100", "ProductLine:Гольфстрим", type="BELONGS_TO", weight=1, sources=[])
    g.add_edge("Model:GS-100", "Component:пусковое реле", type="FAILED", weight=12, sources=[])
    g.add_edge("Model:GS-100", "Part:P-3011", type="HAS_PART", weight=1, sources=[])
    g.add_edge("Part:P-3011", "Part:P-3011B", type="REPLACED_BY", weight=1, sources=[])

    comm = Community(0, sorted(g.nodes), "")
    summary = summarize_community(comm, g, _FakeLLM(["Краткий обзор сообщества. " + " ".join(["текст"] * 180)]))
    assert len(summary.split()) <= 150
    assert "Гольфстрим" in summary
    assert "пусковое реле (12)" in summary
    assert "P-3011 -> P-3011B" in summary


def test_local_search_retries_on_invented_code():
    """Если LLM выдумывает код (SP-205), отсутствующий в фактах, local_search делает повторный запрос."""
    g = nx.DiGraph()
    g.add_node("Model:AR-320", type="Model", name="AR-320", sources=["m.md#0"])
    g.add_node("Part:P-1118B", type="Part", name="P-1118B", sources=["m.md#0"])
    g.add_edge("Model:AR-320", "Part:P-1118B", type="HAS_PART", weight=1, sources=["m.md#0"])
    kb = KnowledgeBase(graph=g, communities=[], vocabulary={})

    llm = _FakeLLM(["Используйте деталь P-1118B и регламент SP-205.", "Используйте деталь P-1118B."])
    ans = local_search("Какая деталь стоит в AR-320?", kb, llm)
    assert not ans.refused
    assert "P-1118B" in ans.text
    assert "SP-205" not in ans.text


def test_global_search_filters_disjoint_product_line_and_rejects_invented_code():
    """global_search отбрасывает ответы чужой линейки и исправляет вымышленные коды на шаге reduce."""
    g = nx.DiGraph()
    g.add_node("ProductLine:Гольфстрим", type="ProductLine", name="Гольфстрим", sources=["a.md#0"])
    g.add_node("ProductLine:Бриз", type="ProductLine", name="Бриз", sources=["b.md#0"])
    g.add_node("Model:GS-100", type="Model", name="GS-100", sources=["a.md#0"])
    g.add_node("Model:BZ-100", type="Model", name="BZ-100", sources=["b.md#0"])
    g.add_edge("Model:GS-100", "ProductLine:Гольфстрим", type="BELONGS_TO", weight=1, sources=["a.md#0"])
    g.add_edge("Model:BZ-100", "ProductLine:Бриз", type="BELONGS_TO", weight=1, sources=["b.md#0"])

    communities = [
        Community(0, ["ProductLine:Гольфстрим", "Model:GS-100"], "Сводка Гольфстрим: лидер GS-100."),
        Community(1, ["ProductLine:Бриз", "Model:BZ-100"], "Сводка Бриз: лидер BZ-100."),
    ]
    kb = KnowledgeBase(graph=g, communities=communities, vocabulary={"ProductLine": ["Гольфстрим", "Бриз"]})
    llm = _FakeLLM(
        [
            '{"answer": "В линейке Гольфстрим лидер GS-100.", "score": 9}',
            '{"answer": "В линейке Бриз лидер BZ-100.", "score": 8}',
            "Лидеры: GS-100 и вымышленная GS-500.",
            "В линейке Гольфстрим лидер GS-100.",
        ]
    )
    ans = global_search("У какой модели в линейке «Гольфстрим» больше всего отказов?", kb, llm)
    assert not ans.refused
    assert "GS-100" in ans.text
    assert "GS-500" not in ans.text
    assert all("Бриз" not in f for f in ans.facts)


def test_agent_preserves_original_question_for_shortened_summarize_topic():
    """Если модель сократила запрос в summarize_topic до названия линейки, передаётся полный исходный вопрос."""
    received: list[str] = []

    def fake_summarize(question: str) -> dict:
        received.append(question)
        return {"answer": "Снята деталь P-3011 (GS-100).", "sources": ["b.md"], "refused": False}

    llm = _FakeLLM(
        [
            ToolCall(id="c1", name="summarize_topic", arguments={"question": "линейка Гольфстрим"}),
            "Снята деталь P-3011 в модели GS-100.",
        ]
    )
    full_q = "Какие детали из линейки «Гольфстрим» сняты с производства и какие модели они затрагивают?"
    res = run_agent(full_q, llm, {"summarize_topic": fake_summarize})
    assert received == [full_q]
    assert "P-3011" in res.answer


def test_agent_reminds_once_to_call_create_service_order_when_requested():
    """При явной просьбе оформить заказ агент напоминает модели вызвать create_service_order."""
    llm = _FakeLLM(
        [
            ToolCall(id="c1", name="search_knowledge", arguments={"question": "E-17 AR-210"}),
            "Актуальная деталь P-1042B. Готов оформить заказ.",
            ToolCall(
                id="c2",
                name="create_service_order",
                arguments={"part_id": "P-1042B", "warehouse": "Казань", "qty": 2, "model": "AR-210"},
            ),
        ]
    )
    tools = {
        "search_knowledge": lambda **_: {
            "answer": "Деталь P-1042B.",
            "facts": ["Part:P-1042 -REPLACED_BY-> Part:P-1042B"],
            "sources": ["b.md"],
            "refused": False,
        },
        "create_service_order": lambda **kw: kw,
    }
    res = run_agent(
        "На AR-210 ошибка E-17. Оформи заказ на 2 штуки актуальной детали на склад Казань.",
        llm,
        tools,
        confirm=False,
    )
    assert res.needs_confirmation is True
    assert res.pending_action == {
        "tool": "create_service_order",
        "args": {"part_id": "P-1042B", "warehouse": "Казань", "qty": 2, "model": "AR-210"},
    }
