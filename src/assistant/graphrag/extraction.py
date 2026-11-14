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
Схема графа знаний и допустимые типы связей (направление строго от subject к object):
- Model -> BELONGS_TO -> ProductLine (модель входит в линейку оборудования)
- Model -> HAS_PART -> Part (в модели штатно установлена деталь)
- Model -> FAILED -> Component (зафиксирован отказ узла в отчёте о выезде)
- Part -> IS_A -> Component (деталь является узлом данного вида)
- Part -> REPLACED_BY -> Part (деталь снята с производства и заменена другой деталью)
- Part -> SUPPLIED_BY -> Supplier (поставщик детали)
- ErrorCode -> INDICATES -> Component (код ошибки указывает на отказ узла)
- ErrorCode -> FIXED_BY -> Procedure (ошибка устраняется по данному регламенту ремонта)

Пример:
Текст: "Деталь P-1042 (пусковое реле) снята с производства. Вместо неё ставится деталь P-1042B. "
       "Поставщик детали P-1042B – «ХолодКомплект»."
Результат:
{
  "entities": [
    {"type": "Part", "name": "P-1042"},
    {"type": "Part", "name": "P-1042B"},
    {"type": "Component", "name": "пусковое реле"},
    {"type": "Supplier", "name": "ХолодКомплект"}
  ],
  "relations": [
    {
      "subject_type": "Part", "subject": "P-1042", "type": "REPLACED_BY",
      "object_type": "Part", "object": "P-1042B"
    },
    {
      "subject_type": "Part", "subject": "P-1042", "type": "IS_A",
      "object_type": "Component", "object": "пусковое реле"
    },
    {
      "subject_type": "Part", "subject": "P-1042B", "type": "SUPPLIED_BY",
      "object_type": "Supplier", "object": "ХолодКомплект"
    }
  ]
}

Возвращай только строгий JSON по схеме. Извлекай только то, что действительно подтверждается текстом чанка.
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

    return ExtractionResult(
        chunk_id=chunk.chunk_id,
        doc_id=chunk.doc_id,
        entities=list(valid_entities.values()),
        relations=valid_relations,
        dropped=dropped,
    )
