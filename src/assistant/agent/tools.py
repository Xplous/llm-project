"""Инструменты агента. Требование FR-6."""

from collections.abc import Callable

from assistant.graphrag.search import global_search, local_search
from assistant.infra.erp_client import ErpClient, ErpNotFound, ErpRejected
from assistant.infra.grounding import code_type, normalize_code
from assistant.infra.llm import LLMClient
from assistant.infra.schemas import KnowledgeBase

WAREHOUSES = ["Москва", "Санкт-Петербург", "Казань", "Новосибирск"]

TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge",
            "description": (
                "Поиск по графу знаний о конкретных моделях, линейках, кодах ошибок, узлах, "
                "деталях, их заменах, поставщиках и регламентах ремонта."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Вопрос с точными кодами моделей/ошибок/деталей и названиями узлов",
                    },
                },
                "required": ["question"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_topic",
            "description": (
                "Обзорный поиск по сводкам сообществ графа знаний: статистика частых отказов "
                "по линейкам и моделям, перечни деталей, снятых с производства."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Обзорный вопрос по линейке оборудования или корпусу документов",
                    },
                },
                "required": ["question"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_stock",
            "description": "Проверка складского остатка детали на складе и признака снятия с производства.",
            "parameters": {
                "type": "object",
                "properties": {
                    "part_id": {
                        "type": "string",
                        "description": "Номер детали вида P-1042 или P-1042B",
                    },
                    "warehouse": {
                        "type": "string",
                        "enum": WAREHOUSES,
                        "description": "Город склада",
                    },
                },
                "required": ["part_id", "warehouse"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_price",
            "description": "Получение актуальной цены детали в рублях и признака снятия с производства.",
            "parameters": {
                "type": "object",
                "properties": {
                    "part_id": {
                        "type": "string",
                        "description": "Номер детали вида P-1042 или P-1042B",
                    },
                },
                "required": ["part_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_service_order",
            "description": "Создание сервисного заказа детали в учётной системе (ERP).",
            "parameters": {
                "type": "object",
                "properties": {
                    "part_id": {
                        "type": "string",
                        "description": "Номер детали вида P-1042 или P-1042B",
                    },
                    "warehouse": {
                        "type": "string",
                        "enum": WAREHOUSES,
                        "description": "Склад назначения",
                    },
                    "qty": {
                        "type": "integer",
                        "description": "Количество деталей (строго больше нуля)",
                    },
                    "model": {
                        "type": "string",
                        "description": "Модель обслуживаемого оборудования",
                    },
                },
                "required": ["model", "part_id", "qty", "warehouse"],
            },
        },
    },
]


def build_tools(kb: KnowledgeBase, llm: LLMClient, erp: ErpClient) -> dict[str, Callable[..., dict]]:
    """Словарь «имя инструмента -> функция». Каждая функция возвращает словарь.

    Функция проверяет свои аргументы до обращения к ERP: склад из списка, номер детали вида P-1042
    или P-1042B, количество больше нуля. При ошибке возвращает {"error": "..."} и ничего не выполняет.
    `ErpNotFound` и `ErpRejected` превращаются в {"error": "..."} с разным текстом, чтобы исходы
    оставались различимыми. `ErpUnavailable` передаётся дальше: повторы делает агент (FR-8).
    """

    def tool_search_knowledge(question: str) -> dict:
        ans = local_search(question, kb, llm)
        return {
            "answer": ans.text,
            "facts": ans.facts,
            "sources": ans.sources,
            "refused": ans.refused,
        }

    def tool_summarize_topic(question: str) -> dict:
        ans = global_search(question, kb, llm)
        return {
            "answer": ans.text,
            "sources": ans.sources,
            "refused": ans.refused,
        }

    def tool_check_stock(part_id: str, warehouse: str) -> dict:
        if warehouse not in WAREHOUSES:
            return {"error": f"неизвестный склад {warehouse}"}
        norm = normalize_code(part_id)
        if not norm or code_type(norm) != "Part":
            return {"error": f"неверный номер детали {part_id}"}
        try:
            return erp.get_stock(part_id=norm, warehouse=warehouse)
        except ErpNotFound:
            return {"error": f"деталь {norm} не найдена"}
        except ErpRejected as exc:
            return {"error": str(exc)}

    def tool_get_price(part_id: str) -> dict:
        norm = normalize_code(part_id)
        if not norm or code_type(norm) != "Part":
            return {"error": f"неверный номер детали {part_id}"}
        try:
            return erp.get_price(part_id=norm)
        except ErpNotFound:
            return {"error": f"деталь {norm} не найдена"}
        except ErpRejected as exc:
            return {"error": str(exc)}

    def tool_create_service_order(part_id: str, warehouse: str, qty: int, model: str) -> dict:
        if warehouse not in WAREHOUSES:
            return {"error": f"неизвестный склад {warehouse}"}
        norm = normalize_code(part_id)
        if not norm or code_type(norm) != "Part":
            return {"error": f"неверный номер детали {part_id}"}
        if not isinstance(qty, int) or qty <= 0:
            return {"error": "количество должно быть больше нуля"}
        try:
            return erp.create_order(part_id=norm, warehouse=warehouse, qty=qty, model=model)
        except ErpNotFound:
            return {"error": f"деталь {norm} не найдена"}
        except ErpRejected as exc:
            return {"error": str(exc)}

    return {
        "search_knowledge": tool_search_knowledge,
        "summarize_topic": tool_summarize_topic,
        "check_stock": tool_check_stock,
        "get_price": tool_get_price,
        "create_service_order": tool_create_service_order,
    }
