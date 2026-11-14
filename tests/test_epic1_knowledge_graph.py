"""Детальные тесты функционала Эпика 1: Извлечение сущностей/связей (FR-1) и сборка графа знаний (FR-2)."""

import json

from assistant.graphrag.extraction import extract_chunk
from assistant.graphrag.graph_builder import build_graph
from assistant.infra.schemas import Chunk, Entity, ExtractionResult, Relation
from assistant.infra.testing import FakeLLM


def _make_extraction_json(entities=(), relations=()) -> str:
    return json.dumps(
        {
            "entities": [{"type": t, "name": n} for t, n in entities],
            "relations": [
                {"subject_type": st, "subject": s, "type": r, "object_type": ot, "object": o}
                for st, s, r, ot, o in relations
            ],
        },
        ensure_ascii=False,
    )


# --- ТЕСТЫ ИЗВЛЕЧЕНИЯ (FR-1) ---


def test_извлечение_корректно_обрабатывает_все_типы_сущностей_и_связей():
    """Проверяет извлечение всех 7 типов сущностей и валидных связей по схеме."""
    chunk_text = (
        "Модель AR-210 входит в линейку Арктика. В ней установлена деталь P-1042 (пусковое реле). "
        "Поставщик детали – ХолодКомплект. Ошибка E-17 указывает на отказ узла пусковое реле и "
        "устраняется по регламенту SP-104. Зафиксирован отказ пусковое реле."
    )
    chunk = Chunk("manual_test.md#0", "manual_test.md", chunk_text)

    llm_payload = _make_extraction_json(
        entities=[
            ("ProductLine", "Арктика"),
            ("Model", "AR-210"),
            ("Part", "P-1042"),
            ("Component", "пусковое реле"),
            ("Supplier", "ХолодКомплект"),
            ("ErrorCode", "E-17"),
            ("Procedure", "SP-104"),
        ],
        relations=[
            ("Model", "AR-210", "BELONGS_TO", "ProductLine", "Арктика"),
            ("Model", "AR-210", "HAS_PART", "Part", "P-1042"),
            ("Part", "P-1042", "IS_A", "Component", "пусковое реле"),
            ("Part", "P-1042", "SUPPLIED_BY", "Supplier", "ХолодКомплект"),
            ("ErrorCode", "E-17", "INDICATES", "Component", "пусковое реле"),
            ("ErrorCode", "E-17", "FIXED_BY", "Procedure", "SP-104"),
            ("Model", "AR-210", "FAILED", "Component", "пусковое реле"),
        ],
    )

    llm = FakeLLM([llm_payload])
    result = extract_chunk(chunk, llm)

    assert result.chunk_id == "manual_test.md#0"
    assert result.doc_id == "manual_test.md"
    assert result.dropped == 0
    assert len(result.relations) == 7

    node_ids = {e.node_id for e in result.entities}
    expected_nodes = {
        "ProductLine:Арктика",
        "Model:AR-210",
        "Part:P-1042",
        "Component:пусковое реле",
        "Supplier:ХолодКомплект",
        "ErrorCode:E-17",
        "Procedure:SP-104",
    }
    assert expected_nodes <= node_ids


def test_извлечение_нормализует_небрежные_коды_и_кириллические_омоглифы():
    """Проверяет приведение кодов к верхнему регистру, замену кириллических букв на латинские."""
    chunk_text = "Витрина ar 210, деталь р-1042b заменена. Ошибка е-17 устраняется по регламенту sp-104."
    chunk = Chunk("report_sloppy.md#0", "report_sloppy.md", chunk_text)

    llm_payload = _make_extraction_json(
        entities=[
            ("Model", "AR-210"),
            ("Part", "P-1042B"),
            ("ErrorCode", "E-17"),
            ("Procedure", "SP-104"),
        ],
        relations=[
            ("ErrorCode", "E-17", "FIXED_BY", "Procedure", "SP-104"),
        ],
    )

    llm = FakeLLM([llm_payload])
    result = extract_chunk(chunk, llm)

    assert result.dropped == 0
    found_nodes = {e.node_id for e in result.entities}
    assert {"Model:AR-210", "Part:P-1042B", "ErrorCode:E-17", "Procedure:SP-104"} <= found_nodes


def test_извлечение_отбрасывает_коды_которых_нет_в_тексте_чанка():
    """Проверяет, что выдуманные коды деталей/моделей отбрасываются вместе со связями."""
    chunk_text = "В модели AR-210 установлена деталь P-1042."
    chunk = Chunk("manual_simple.md#0", "manual_simple.md", chunk_text)

    llm_payload = _make_extraction_json(
        entities=[
            ("Model", "AR-210"),
            ("Part", "P-1042"),
            ("Part", "P-9999"),  # нет в тексте
            ("ErrorCode", "E-99"),  # нет в тексте
        ],
        relations=[
            ("Model", "AR-210", "HAS_PART", "Part", "P-1042"),
            ("Model", "AR-210", "HAS_PART", "Part", "P-9999"),  # должна быть отброшена
            ("ErrorCode", "E-99", "INDICATES", "Component", "пусковое реле"),  # должна быть отброшена
        ],
    )

    llm = FakeLLM([llm_payload])
    result = extract_chunk(chunk, llm)

    node_ids = {e.node_id for e in result.entities}
    assert "Part:P-9999" not in node_ids
    assert "ErrorCode:E-99" not in node_ids
    assert len(result.relations) == 1
    assert result.relations[0].object.name == "P-1042"
    assert result.dropped >= 4  # 2 сущности + 2 связи


def test_извлечение_отбрасывает_названия_не_из_словаря():
    """Проверяет, что сущности не из словаря (например, выдуманный поставщик или узел) отбрасываются."""
    chunk_text = "Деталь P-1042 поставляется поставщиком НеизвестныйПоставщик и является узлом турбина."
    chunk = Chunk("bulletin_fake.md#0", "bulletin_fake.md", chunk_text)

    llm_payload = _make_extraction_json(
        entities=[
            ("Part", "P-1042"),
            ("Supplier", "НеизвестныйПоставщик"),  # нет в словаре
            ("Component", "турбина"),  # нет в словаре
        ],
        relations=[
            ("Part", "P-1042", "SUPPLIED_BY", "Supplier", "НеизвестныйПоставщик"),
            ("Part", "P-1042", "IS_A", "Component", "турбина"),
        ],
    )

    llm = FakeLLM([llm_payload])
    result = extract_chunk(chunk, llm)

    assert len(result.relations) == 0
    node_ids = {e.node_id for e in result.entities}
    assert "Supplier:НеизвестныйПоставщик" not in node_ids
    assert "Component:турбина" not in node_ids
    assert result.dropped >= 4


def test_извлечение_приводит_названия_из_словаря_к_каноническому_виду():
    """Проверяет канонизацию названий из словаря (ООО «ХолодКомплект» -> ХолодКомплект)."""
    chunk_text = "Деталь P-1042 поставляется компанией ООО «ХолодКомплект»."
    chunk = Chunk("bulletin_supplier.md#0", "bulletin_supplier.md", chunk_text)

    llm_payload = _make_extraction_json(
        entities=[
            ("Part", "P-1042"),
            ("Supplier", "ООО «ХолодКомплект»"),
        ],
        relations=[
            ("Part", "P-1042", "SUPPLIED_BY", "Supplier", "ООО «ХолодКомплект»"),
        ],
    )

    llm = FakeLLM([llm_payload])
    result = extract_chunk(chunk, llm)

    assert result.dropped == 0
    supplier_nodes = [e for e in result.entities if e.type == "Supplier"]
    assert len(supplier_nodes) == 1
    assert supplier_nodes[0].name == "ХолодКомплект"
    assert result.relations[0].object.name == "ХолодКомплект"


def test_извлечение_делает_повтор_при_первом_невалидном_json_и_успешно_разбирает_второй():
    """Проверяет ровно 1 повторный вызов при битом JSON и успешный разбор со второй попытки."""
    chunk_text = "В витрине AR-210 используется пусковое реле P-1042."
    chunk = Chunk("manual_retry.md#0", "manual_retry.md", chunk_text)

    good_payload = _make_extraction_json(
        entities=[("Model", "AR-210"), ("Part", "P-1042")],
        relations=[("Model", "AR-210", "HAS_PART", "Part", "P-1042")],
    )

    llm = FakeLLM(["{broken json...", good_payload])
    result = extract_chunk(chunk, llm)

    assert len(llm.requests) == 2
    assert len(result.relations) == 1
    assert result.relations[0].subject.name == "AR-210"


def test_извлечение_возвращает_пустой_результат_после_двух_неудачных_попыток_json():
    """Проверяет безопасный возврат пустого ExtractionResult после двух сбоев ответа модели."""
    chunk = Chunk("manual_fail.md#0", "manual_fail.md", "Текст чанка")
    llm = FakeLLM(["не json", "тоже не json"])

    result = extract_chunk(chunk, llm)

    assert len(llm.requests) == 2
    assert result.chunk_id == "manual_fail.md#0"
    assert result.entities == []
    assert result.relations == []
    assert result.dropped == 0


def test_извлечение_отбрасывает_связи_с_неверной_сигнатурой_типов():
    """Проверяет фильтрацию связей, где типы концов противоречат RELATION_SIGNATURES."""
    chunk_text = "В витрине AR-210 установлена деталь P-1042."
    chunk = Chunk("manual_sig.md#0", "manual_sig.md", chunk_text)

    llm_payload = _make_extraction_json(
        entities=[("Model", "AR-210"), ("Part", "P-1042")],
        relations=[
            ("Model", "AR-210", "REPLACED_BY", "Part", "P-1042"),  # REPLACED_BY допустима только Part -> Part
            ("Model", "AR-210", "HAS_PART", "Part", "P-1042"),  # валидная связь
        ],
    )

    llm = FakeLLM([llm_payload])
    result = extract_chunk(chunk, llm)

    assert len(result.relations) == 1
    assert result.relations[0].type == "HAS_PART"
    assert result.dropped >= 1


# --- ТЕСТЫ ПОСТРОЕНИЯ ГРАФА (FR-2) ---


def test_сборка_графа_создает_узлы_с_полными_атрибутами_и_списком_источников():
    """Проверяет корректность добавления узлов, атрибутов type, name и источников."""
    res1 = ExtractionResult(
        chunk_id="doc1.md#0",
        doc_id="doc1.md",
        entities=[Entity("Model", "AR-210"), Entity("Part", "P-1042")],
        relations=[Relation(Entity("Model", "AR-210"), "HAS_PART", Entity("Part", "P-1042"))],
    )
    res2 = ExtractionResult(
        chunk_id="doc2.md#1",
        doc_id="doc2.md",
        entities=[Entity("Part", "P-1042"), Entity("Part", "P-1042B")],
        relations=[Relation(Entity("Part", "P-1042"), "REPLACED_BY", Entity("Part", "P-1042B"))],
    )

    graph = build_graph([res1, res2])

    assert set(graph.nodes) == {"Model:AR-210", "Part:P-1042", "Part:P-1042B"}
    p1042 = graph.nodes["Part:P-1042"]
    assert p1042["type"] == "Part"
    assert p1042["name"] == "P-1042"
    assert sorted(p1042["sources"]) == ["doc1.md#0", "doc2.md#1"]


def test_сборка_графа_считает_вес_ребра_по_числу_уникальных_чанков():
    """Проверяет, что дубли одной связи в рамках одного чанка не завышают вес."""
    rel = Relation(Entity("Part", "P-1042"), "IS_A", Entity("Component", "пусковое реле"))
    # В первом чанке связь повторена дважды, во втором один раз
    res1 = ExtractionResult("c1.md#0", "c1.md", [], [rel, rel])
    res2 = ExtractionResult("c2.md#0", "c2.md", [], [rel])

    graph = build_graph([res1, res2])
    edge = graph.edges["Part:P-1042", "Component:пусковое реле"]

    assert edge["type"] == "IS_A"
    assert edge["weight"] == 2
    assert sorted(edge["sources"]) == ["c1.md#0", "c2.md#0"]


def test_сборка_графа_разрешает_встречные_замены_в_пользу_большего_веса():
    """Проверяет выбор связи с большим весом при противоположных REPLACED_BY."""
    fwd = Relation(Entity("Part", "P-1042"), "REPLACED_BY", Entity("Part", "P-1042B"))
    bwd = Relation(Entity("Part", "P-1042B"), "REPLACED_BY", Entity("Part", "P-1042"))

    results = [
        ExtractionResult("a.md#0", "a.md", [], [fwd]),
        ExtractionResult("b.md#0", "b.md", [], [fwd]),
        ExtractionResult("c.md#0", "c.md", [], [fwd]),
        ExtractionResult("d.md#0", "d.md", [], [bwd]),
    ]

    graph = build_graph(results)

    assert graph.has_edge("Part:P-1042", "Part:P-1042B")
    assert not graph.has_edge("Part:P-1042B", "Part:P-1042")
    assert graph.edges["Part:P-1042", "Part:P-1042B"]["weight"] == 3
    assert graph.graph["conflicts"] == 1


def test_сборка_графа_удаляет_обе_встречные_замены_при_равных_весах():
    """Проверяет удаление обеих связей при равных весах противоположных замен."""
    fwd = Relation(Entity("Part", "P-1042"), "REPLACED_BY", Entity("Part", "P-1042B"))
    bwd = Relation(Entity("Part", "P-1042B"), "REPLACED_BY", Entity("Part", "P-1042"))

    results = [
        ExtractionResult("a.md#0", "a.md", [], [fwd]),
        ExtractionResult("b.md#0", "b.md", [], [bwd]),
    ]

    graph = build_graph(results)

    assert not graph.has_edge("Part:P-1042", "Part:P-1042B")
    assert not graph.has_edge("Part:P-1042B", "Part:P-1042")
    assert graph.graph["conflicts"] == 1


def test_сборка_графа_разрешает_несколько_независимых_конфликтов_замен():
    """Проверяет подсчёт conflicts при нескольких независимых конфликтах замен в графе."""
    # Пара 1: P-1042 <-> P-1042B (вес 2 против 1 -> побеждает forward)
    fwd1 = Relation(Entity("Part", "P-1042"), "REPLACED_BY", Entity("Part", "P-1042B"))
    bwd1 = Relation(Entity("Part", "P-1042B"), "REPLACED_BY", Entity("Part", "P-1042"))

    # Пара 2: P-2001 <-> P-2002 (вес 1 против 1 -> удаляются обе)
    fwd2 = Relation(Entity("Part", "P-2001"), "REPLACED_BY", Entity("Part", "P-2002"))
    bwd2 = Relation(Entity("Part", "P-2002"), "REPLACED_BY", Entity("Part", "P-2001"))

    results = [
        ExtractionResult("c1.md#0", "c1.md", [], [fwd1, fwd2]),
        ExtractionResult("c2.md#0", "c2.md", [], [fwd1, bwd2]),
        ExtractionResult("c3.md#0", "c3.md", [], [bwd1]),
    ]

    graph = build_graph(results)

    assert graph.has_edge("Part:P-1042", "Part:P-1042B")
    assert not graph.has_edge("Part:P-1042B", "Part:P-1042")
    assert not graph.has_edge("Part:P-2001", "Part:P-2002")
    assert not graph.has_edge("Part:P-2002", "Part:P-2001")
    assert graph.graph["conflicts"] == 2
