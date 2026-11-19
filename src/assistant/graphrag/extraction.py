"""Извлечение сущностей и связей из чанка. Требование FR-1."""

import json

from assistant.infra.config import vocabulary
from assistant.infra.grounding import CODE_TYPES, canonical_name, find_codes
from assistant.infra.llm import LLMClient
from assistant.infra.schemas import (
    ENTITY_TYPES,
    EXTRACTION_SCHEMA,
    Chunk,
    Entity,
    ExtractionResult,
    Relation,
)

SYSTEM_PROMPT = """Ты анализируешь фрагменты технической документации компании «ПолярТех» и извлекаешь граф знаний.

Типы сущностей (`entities`):
- `ProductLine`: линейка (строго из словаря: «Арктика», «Бриз», «Гольфстрим»; слова «витрина», «моноблок» — НЕ линейки)
- `Model`: код модели (например, AR-210, BZ-110, GS-410)
- `Part`: номер детали (например, P-1042, P-1042B)
- `Component`: название узла (например, «пусковое реле», «компрессор»)
- `ErrorCode`: код ошибки (например, E-17, E-22)
- `Procedure`: номер регламента (например, SP-104)
- `Supplier`: название поставщика (например, «ХолодКомплект»)

Допустимые типы связей (`relations`, направление строго `subject -> type -> object`):
- Model -> BELONGS_TO -> ProductLine (модель входит в линейку)
- Model -> HAS_PART -> Part (в модели установлена деталь; НЕ используй HAS_PART от Part к Component!)
- Part -> IS_A -> Component (деталь является узлом данного вида)
- Part -> REPLACED_BY -> Part (деталь снята с производства и заменена новой деталью)
- Part -> SUPPLIED_BY -> Supplier (поставщик детали)
- ErrorCode -> INDICATES -> Component (код ошибки указывает на отказ узла)
- ErrorCode -> FIXED_BY -> Procedure (ошибка устраняется по регламенту SP-xxx; от кода ошибки к регламенту!)
- Model -> FAILED -> Component (в отчёте о выезде зафиксирован отказ узла у модели; от Model к Component!)

Важные правила:
1. В разделе «Состав узлов» руководства модели для КАЖДОЙ строки списка без пропусков
   `- <узел> – деталь <P-код>, поставщик «<Поставщик>»` извлекай сразу три связи:
   (Model HAS_PART Part), (Part IS_A Component) и (Part SUPPLIED_BY Supplier).
2. В отчётах о выезде извлекай (Model FAILED Component) и, если указан код ошибки, (ErrorCode INDICATES Component).
3. В регламентах ремонта извлекай (ErrorCode FIXED_BY Procedure) и (ErrorCode INDICATES Component).
   Для плановых регламентов без кодов ошибок возвращай пустые списки `"entities": []` и `"relations": []`.

Пример 1 (Руководство по эксплуатации):
Текст: "Витрина AR-900 входит в линейку «Арктика». В AR-900 установлены узлы:\n"
       "- пусковое реле – деталь P-9001, поставщик «ХолодКомплект»\n"
       "- компрессор – деталь P-9002, поставщик «КомпрессорМаш»\n"
       "Коды ошибок: E-91 – отказ узла «пусковое реле»."
Результат:
{
  "entities": [
    {"type": "Model", "name": "AR-900"},
    {"type": "ProductLine", "name": "Арктика"},
    {"type": "Part", "name": "P-9001"},
    {"type": "Part", "name": "P-9002"},
    {"type": "Component", "name": "пусковое реле"},
    {"type": "Component", "name": "компрессор"},
    {"type": "Supplier", "name": "ХолодКомплект"},
    {"type": "Supplier", "name": "КомпрессорМаш"},
    {"type": "ErrorCode", "name": "E-91"}
  ],
  "relations": [
    {"subject_type": "Model", "subject": "AR-900", "type": "BELONGS_TO",
     "object_type": "ProductLine", "object": "Арктика"},
    {"subject_type": "Model", "subject": "AR-900", "type": "HAS_PART",
     "object_type": "Part", "object": "P-9001"},
    {"subject_type": "Part", "subject": "P-9001", "type": "IS_A",
     "object_type": "Component", "object": "пусковое реле"},
    {"subject_type": "Part", "subject": "P-9001", "type": "SUPPLIED_BY",
     "object_type": "Supplier", "object": "ХолодКомплект"},
    {"subject_type": "Model", "subject": "AR-900", "type": "HAS_PART",
     "object_type": "Part", "object": "P-9002"},
    {"subject_type": "Part", "subject": "P-9002", "type": "IS_A",
     "object_type": "Component", "object": "компрессор"},
    {"subject_type": "Part", "subject": "P-9002", "type": "SUPPLIED_BY",
     "object_type": "Supplier", "object": "КомпрессорМаш"},
    {"subject_type": "ErrorCode", "subject": "E-91", "type": "INDICATES",
     "object_type": "Component", "object": "пусковое реле"}
  ]
}

Пример 2 (Сервисный бюллетень):
Текст: "Деталь P-9001 (пусковое реле) снята с производства. Вместо неё ставится деталь P-9001B. "
       "Поставщик детали P-9001B – «ХолодКомплект»."
Результат:
{
  "entities": [
    {"type": "Part", "name": "P-9001"},
    {"type": "Part", "name": "P-9001B"},
    {"type": "Component", "name": "пусковое реле"},
    {"type": "Supplier", "name": "ХолодКомплект"}
  ],
  "relations": [
    {"subject_type": "Part", "subject": "P-9001", "type": "REPLACED_BY",
     "object_type": "Part", "object": "P-9001B"},
    {"subject_type": "Part", "subject": "P-9001", "type": "IS_A",
     "object_type": "Component", "object": "пусковое реле"},
    {"subject_type": "Part", "subject": "P-9001B", "type": "SUPPLIED_BY",
     "object_type": "Supplier", "object": "ХолодКомплект"}
  ]
}

Пример 3 (Регламент ремонта):
Текст: "Регламент SP-901 применяется при ошибке E-91. Ошибка E-91 указывает на отказ узла «пусковое реле»."
Результат:
{
  "entities": [
    {"type": "Procedure", "name": "SP-901"},
    {"type": "ErrorCode", "name": "E-91"},
    {"type": "Component", "name": "пусковое реле"}
  ],
  "relations": [
    {"subject_type": "ErrorCode", "subject": "E-91", "type": "FIXED_BY",
     "object_type": "Procedure", "object": "SP-901"},
    {"subject_type": "ErrorCode", "subject": "E-91", "type": "INDICATES",
     "object_type": "Component", "object": "пусковое реле"}
  ]
}

Пример 4 (Отчёт о выезде):
Текст: "Оборудование: моноблок BZ-900. На панели горел код Е-92. Диагностика показала отказ узла: датчик температуры."
Результат:
{
  "entities": [
    {"type": "Model", "name": "BZ-900"},
    {"type": "ErrorCode", "name": "E-92"},
    {"type": "Component", "name": "датчик температуры"}
  ],
  "relations": [
    {"subject_type": "Model", "subject": "BZ-900", "type": "FAILED",
     "object_type": "Component", "object": "датчик температуры"},
    {"subject_type": "ErrorCode", "subject": "E-92", "type": "INDICATES",
     "object_type": "Component", "object": "датчик температуры"}
  ]
}

Возвращай только строгий JSON по схеме. Извлекай только то, что подтверждается текстом фрагмента.
"""


def _parse_extraction_payload(raw_content: str) -> dict | None:
    try:
        data = json.loads(raw_content)
    except Exception:
        return None

    if not isinstance(data, dict):
        return None
    if "entities" not in data or "relations" not in data:
        return None
    if not isinstance(data["entities"], list) or not isinstance(data["relations"], list):
        return None

    for item in data["entities"]:
        if not isinstance(item, dict):
            return None
        if "type" not in item or "name" not in item:
            return None
        if not isinstance(item["type"], str) or not isinstance(item["name"], str):
            return None

    for item in data["relations"]:
        if not isinstance(item, dict):
            return None
        required_keys = ["subject_type", "subject", "type", "object_type", "object"]
        if any(k not in item or not isinstance(item[k], str) for k in required_keys):
            return None

    return data


def extract_chunk(chunk: Chunk, llm: LLMClient) -> ExtractionResult:
    """Возвращает сущности и связи чанка строго по схеме графа.

    Модель вызывается через `llm.chat(..., json_schema=EXTRACTION_SCHEMA)`. Запрос описывает схему
    с направлением каждой связи и содержит хотя бы один пример. Всё, что не подтверждается текстом,
    отбрасывается и считается в `dropped`: код, которого нет в чанке, название не из словаря,
    связь с отброшенным концом. Пригодятся `find_codes` и `canonical_name` из `assistant.infra.grounding`.
    Функция не падает ни на каком ответе модели: одна повторная попытка, затем пустой результат.
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Документ: {chunk.doc_id}\nТекст фрагмента:\n{chunk.text}"},
    ]

    data = None
    for _ in range(2):
        response = llm.chat(messages, json_schema=EXTRACTION_SCHEMA, max_tokens=4096)
        data = _parse_extraction_payload(response.content)
        if data is not None:
            break

    if data is None:
        return ExtractionResult(chunk.chunk_id, chunk.doc_id, [], [])

    vocab = vocabulary()
    chunk_codes = set(find_codes(chunk.text))

    valid_entities: dict[str, Entity] = {}
    dropped = 0

    def validate_entity_spec(entity_type: str, raw_name: str) -> Entity | None:
        if entity_type not in ENTITY_TYPES:
            return None
        canon = canonical_name(entity_type, raw_name, vocab)
        if not canon:
            return None
        if entity_type in CODE_TYPES and canon not in chunk_codes:
            return None
        return Entity(type=entity_type, name=canon)

    for item in data["entities"]:
        e_type = item.get("type", "")
        e_name = item.get("name", "")
        entity = validate_entity_spec(e_type, e_name)
        if entity is None:
            dropped += 1
        else:
            valid_entities[entity.node_id] = entity

    valid_relations: list[Relation] = []
    seen_relations: set[tuple[str, str, str]] = set()

    for item in data["relations"]:
        s_type = item.get("subject_type", "")
        s_name = item.get("subject", "")
        r_type = item.get("type", "")
        o_type = item.get("object_type", "")
        o_name = item.get("object", "")

        subject_ent = validate_entity_spec(s_type, s_name)
        if subject_ent is None:
            dropped += 1
            continue

        object_ent = validate_entity_spec(o_type, o_name)
        if object_ent is None:
            dropped += 1
            continue

        relation = Relation(subject=subject_ent, type=r_type, object=object_ent)
        if not relation.matches_schema():
            dropped += 1
            continue

        key = (subject_ent.node_id, r_type, object_ent.node_id)
        if key not in seen_relations:
            seen_relations.add(key)
            valid_relations.append(relation)

        if subject_ent.node_id not in valid_entities:
            valid_entities[subject_ent.node_id] = subject_ent
        if object_ent.node_id not in valid_entities:
            valid_entities[object_ent.node_id] = object_ent

    if not valid_relations and valid_entities and {e.type for e in valid_entities.values()} == {"Procedure"}:
        valid_entities.clear()

    return ExtractionResult(
        chunk_id=chunk.chunk_id,
        doc_id=chunk.doc_id,
        entities=list(valid_entities.values()),
        relations=valid_relations,
        dropped=dropped,
    )
