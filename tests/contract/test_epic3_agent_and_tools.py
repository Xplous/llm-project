"""Детальные тесты функционала Эпика 3: Инструменты ERP (FR-6) и диалоговый цикл агента (FR-7 — FR-10)."""

from collections.abc import Callable

import pytest

from assistant.agent.agent import run_agent
from assistant.agent.tools import TOOL_SCHEMAS, WAREHOUSES, build_tools
from assistant.infra.erp_client import ErpNotFound, ErpRejected, ErpUnavailable
from assistant.infra.llm import LLMResponse, ToolCall
from assistant.infra.schemas import KnowledgeBase
from assistant.infra.testing import FakeLLM


def call(name: str, **arguments) -> LLMResponse:
    return LLMResponse("", [ToolCall(f"call-{name}", name, arguments)])


class MockErp:
    """Мок ERP-системы с учётом склада, цен, остатков и проверки статуса деталей."""

    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def warehouses(self) -> list[str]:
        return WAREHOUSES

    def get_price(self, part_id: str) -> dict:
        self.calls.append(("get_price", part_id))
        if part_id == "P-1042":
            return {"part_id": part_id, "name": "пусковое реле старое", "price_rub": 2100, "discontinued": True}
        if part_id == "P-1042B":
            return {"part_id": part_id, "name": "пусковое реле", "price_rub": 2630, "discontinued": False}
        raise ErpNotFound(f"деталь {part_id} не найдена")

    def get_stock(self, part_id: str, warehouse: str) -> dict:
        self.calls.append(("get_stock", part_id, warehouse))
        if part_id not in ("P-1042", "P-1042B"):
            raise ErpNotFound(f"деталь {part_id} не найдена")
        qty = 5 if warehouse == "Казань" else 0
        return {"part_id": part_id, "warehouse": warehouse, "qty": qty, "discontinued": part_id == "P-1042"}

    def create_order(self, part_id: str, warehouse: str, qty: int, model: str) -> dict:
        self.calls.append(("create_order", part_id, warehouse, qty, model))
        if part_id == "P-1042":
            raise ErpRejected("деталь P-1042 снята с производства, заказ невозможен")
        return {
            "order_id": "SO-777001",
            "part_id": part_id,
            "warehouse": warehouse,
            "qty": qty,
            "model": model,
            "status": "created",
        }


class MockToolsHelper:
    """Управляемый набор мок-инструментов для тестирования агента."""

    def __init__(self, **overrides) -> None:
        self.call_history: list[tuple[str, dict]] = []
        self._registry = {
            "search_knowledge": {
                "answer": "В AR-210 установлена деталь P-1042, заменена на P-1042B.",
                "facts": ["P-1042 -REPLACED_BY-> P-1042B"],
                "sources": ["bulletin_SB-2025-01.md"],
                "refused": False,
            },
            "summarize_topic": {"answer": "Сводка отказов.", "sources": [], "refused": False},
            "check_stock": {"part_id": "P-1042B", "warehouse": "Казань", "qty": 5, "discontinued": False},
            "get_price": {"part_id": "P-1042B", "name": "пусковое реле", "price_rub": 2630, "discontinued": False},
            "create_service_order": {
                "order_id": "SO-777001",
                "part_id": "P-1042B",
                "warehouse": "Казань",
                "qty": 2,
                "model": "AR-210",
                "status": "created",
            },
            **overrides,
        }

    def as_dict(self) -> dict[str, Callable[..., dict]]:
        def wrap(name: str):
            def execute(**kwargs) -> dict:
                self.call_history.append((name, kwargs))
                item = self._registry[name]
                return item(**kwargs) if callable(item) else item

            return execute

        return {k: wrap(k) for k in self._registry}

    def count(self, name: str) -> int:
        return sum(1 for called_name, _ in self.call_history if called_name == name)


@pytest.fixture()
def erp() -> MockErp:
    return MockErp()


@pytest.fixture()
def kb() -> KnowledgeBase:
    import networkx as nx

    return KnowledgeBase(nx.DiGraph(), [], {})


# --- ТЕСТЫ ИНСТРУМЕНТОВ (FR-6) ---


def test_tool_schemas_содержит_все_пять_инструментов_и_строгий_enum_складов():
    """Проверяет структуру схем OpenAI function calling для всех 5 инструментов."""
    by_name = {s["function"]["name"]: s["function"] for s in TOOL_SCHEMAS}
    expected = {"search_knowledge", "summarize_topic", "check_stock", "get_price", "create_service_order"}
    assert set(by_name.keys()) == expected

    stock_params = by_name["check_stock"]["parameters"]
    assert stock_params["properties"]["warehouse"]["enum"] == WAREHOUSES
    assert sorted(stock_params["required"]) == ["part_id", "warehouse"]

    order_params = by_name["create_service_order"]["parameters"]
    assert sorted(order_params["required"]) == ["model", "part_id", "qty", "warehouse"]


def test_build_tools_check_stock_валидирует_город_склада(kb, erp):
    """Проверяет отказ инструмента при неизвестном складе без обращения к ERP."""
    tools = build_tools(kb, FakeLLM([]), erp)
    res = tools["check_stock"](part_id="P-1042B", warehouse="Владивосток")
    assert "error" in res
    assert "неизвестный склад" in res["error"]
    assert len(erp.calls) == 0


def test_build_tools_check_stock_валидирует_номер_детали(kb, erp):
    """Проверяет отказ при передаче некорректного кода детали (например, имени модели)."""
    tools = build_tools(kb, FakeLLM([]), erp)
    res = tools["check_stock"](part_id="AR-210", warehouse="Казань")
    assert "error" in res
    assert "неверный номер детали" in res["error"]
    assert len(erp.calls) == 0


def test_build_tools_create_service_order_запрещает_нулевое_или_отрицательное_количество(kb, erp):
    """Проверяет отклонение заказов с неположительным количеством деталей."""
    tools = build_tools(kb, FakeLLM([]), erp)
    order_args = {"part_id": "P-1042B", "warehouse": "Казань", "model": "AR-210"}

    res_zero = tools["create_service_order"](qty=0, **order_args)
    assert "error" in res_zero
    assert "больше нуля" in res_zero["error"]

    res_neg = tools["create_service_order"](qty=-3, **order_args)
    assert "error" in res_neg
    assert "больше нуля" in res_neg["error"]
    assert len(erp.calls) == 0


def test_build_tools_отличает_отсутствие_детали_в_erp_от_нулевого_остатка(kb):
    """Проверяет сохранение различимости между нулевым остатком (успех) и ErpNotFound (ошибка)."""
    mock_erp = MockErp()
    tools = build_tools(kb, FakeLLM([]), mock_erp)

    # Деталь есть в ERP, но остаток на складе в Москве равен 0
    zero_stock = tools["check_stock"](part_id="P-1042B", warehouse="Москва")
    assert zero_stock["qty"] == 0
    assert "error" not in zero_stock

    # Детали вообще нет в базе ERP
    missing = tools["check_stock"](part_id="P-9999", warehouse="Москва")
    assert "error" in missing
    assert "не найдена" in missing["error"]
    assert "qty" not in missing


def test_build_tools_сообщает_об_ошибке_при_заказе_снятой_с_производства_детали(kb):
    """Проверяет понятное сообщение об ошибке при попытке заказа снятой с производства детали."""
    mock_erp = MockErp()
    tools = build_tools(kb, FakeLLM([]), mock_erp)

    res = tools["create_service_order"](part_id="P-1042", warehouse="Казань", qty=1, model="AR-210")
    assert "error" in res
    assert "снята с производства" in res["error"]


# --- ТЕСТЫ АГЕНТА (FR-7 — FR-10) ---


def test_run_agent_успешно_связывает_поиск_по_графу_и_запрос_цены():
    """Проверяет цепочку рассуждений агента: поиск детали по базе -> проверка цены в ERP -> итоговый ответ."""
    helper = MockToolsHelper()
    llm = FakeLLM(
        [
            call("search_knowledge", question="Какую деталь заказать при ошибке E-17 на AR-210?"),
            call("get_price", part_id="P-1042B"),
            "Для модели AR-210 при ошибке E-17 закажите деталь P-1042B, цена 2630 руб.",
        ]
    )

    res = run_agent("Какую деталь заказать при ошибке E-17 на AR-210 и сколько она стоит?", llm, helper.as_dict())

    assert not res.refused
    assert len(res.steps) == 2
    assert res.steps[0].tool == "search_knowledge"
    assert res.steps[1].tool == "get_price"
    assert "bulletin_SB-2025-01.md" in res.sources
    assert "2630" in res.answer


def test_run_agent_блокирует_вызов_инструмента_с_неподтвержденным_номером_детали():
    """Проверяет, что агент не отправляет в ERP код детали, которого не было ни в вопросе, ни в результатах поиска."""
    helper = MockToolsHelper()
    llm = FakeLLM(
        [
            call("get_price", part_id="P-9999"),  # выдуманный код
            "Не могу проверить цену: номер детали неизвестен.",
        ]
    )

    res = run_agent("Сколько стоит компрессор для модели AR-210?", llm, helper.as_dict())

    assert helper.count("get_price") == 0  # инструмент не был вызван
    assert res.steps[0].error is not None
    assert "не подтверждён" in res.steps[0].error


def test_run_agent_блокирует_создание_заказа_если_количество_не_названо_в_вопросе():
    """Проверяет, что при отсутствии явного количества в вопросе заказ не формируется даже при confirm=True."""
    helper = MockToolsHelper()
    llm = FakeLLM(
        [
            call("create_service_order", part_id="P-1042B", warehouse="Казань", qty=1, model="AR-210"),
            "Уточните, пожалуйста, количество деталей для заказа.",
        ]
    )

    # В вопросе нет числа 1
    res = run_agent("Закажи деталь P-1042B для AR-210 на склад Казань.", llm, helper.as_dict(), confirm=True)

    assert helper.count("create_service_order") == 0
    assert not res.needs_confirmation
    assert res.pending_action is None
    assert "Уточните" in res.answer


def test_run_agent_требует_подтверждения_диспетчера_при_confirm_false():
    """Проверяет Human-in-the-loop: при confirm=False агент останавливается с needs_confirmation=True."""
    helper = MockToolsHelper()
    order_args = {"part_id": "P-1042B", "warehouse": "Казань", "qty": 2, "model": "AR-210"}
    llm = FakeLLM([call("create_service_order", **order_args)])

    res = run_agent("Оформи заказ: 2 шт P-1042B для AR-210 в Казань.", llm, helper.as_dict(), confirm=False)

    assert helper.count("create_service_order") == 0
    assert res.needs_confirmation is True
    assert res.pending_action == {"tool": "create_service_order", "args": order_args}


def test_run_agent_создает_заказ_при_confirm_true():
    """Проверяет создание заказа в ERP при получении подтверждения confirm=True."""
    helper = MockToolsHelper()
    order_args = {"part_id": "P-1042B", "warehouse": "Казань", "qty": 2, "model": "AR-210"}
    llm = FakeLLM(
        [
            call("create_service_order", **order_args),
            "Заказ SO-777001 успешно сформирован.",
        ]
    )

    res = run_agent("Оформи заказ: 2 шт P-1042B для AR-210 в Казань.", llm, helper.as_dict(), confirm=True)

    assert helper.count("create_service_order") == 1
    assert not res.needs_confirmation
    assert res.pending_action is None
    assert "SO-777001" in res.answer


def test_run_agent_повторяет_запрос_при_временной_недоступности_erp_до_двух_раз():
    """Проверяет механизм retry (до 3 попыток всего) при исключении ErpUnavailable."""
    tries = 0

    def flaky_stock(**kwargs):
        nonlocal tries
        tries += 1
        if tries < 3:
            raise ErpUnavailable("Временный сбой сети ERP")
        return {"part_id": "P-1042B", "warehouse": "Казань", "qty": 5, "discontinued": False}

    helper = MockToolsHelper(check_stock=flaky_stock)
    llm = FakeLLM(
        [
            call("check_stock", part_id="P-1042B", warehouse="Казань"),
            "Остаток детали P-1042B в Казани составляет 5 шт.",
        ]
    )

    res = run_agent("Сколько штук P-1042B есть в Казани?", llm, helper.as_dict())

    assert tries == 3
    assert res.steps[0].error is None
    assert res.steps[0].result["qty"] == 5
    assert "5 шт" in res.answer


def test_run_agent_не_выполняет_повторно_инструмент_с_идентичными_аргументами():
    """Проверяет дедупликацию вызовов инструментов с одинаковыми аргументами."""
    helper = MockToolsHelper()
    llm = FakeLLM(
        [
            call("get_price", part_id="P-1042B"),
            call("get_price", part_id="P-1042B"),  # повторный идентичный вызов
            "Цена детали P-1042B – 2630 руб.",
        ]
    )

    res = run_agent("Сколько стоит деталь P-1042B?", llm, helper.as_dict())

    assert helper.count("get_price") == 1  # вызван фактически только 1 раз
    assert res.answer == "Цена детали P-1042B – 2630 руб."


def test_run_agent_просит_модель_исправить_ответ_при_выдуманной_цене():
    """Проверяет верификацию ответа: запрос исправления при обнаружении цены, не подтверждённой ERP."""
    helper = MockToolsHelper()
    llm = FakeLLM(
        [
            call("get_price", part_id="P-1042B"),
            "Цена детали составляет 9999 руб.",  # выдуманная цена
            "Цена детали составляет 2630 руб.",  # исправленная цена
        ]
    )

    res = run_agent("Сколько стоит P-1042B?", llm, helper.as_dict())

    assert len(llm.requests) == 3
    assert res.answer == "Цена детали составляет 2630 руб."
    assert not res.refused


def test_run_agent_отказывает_если_модель_дважды_выдает_выдуманные_данные():
    """Проверяет возврат отказа, если модель повторно выдает галлюцинацию после запроса на исправление."""
    helper = MockToolsHelper()
    llm = FakeLLM(
        [
            call("get_price", part_id="P-1042B"),
            "Цена детали составляет 9999 руб.",  # первая попытка
            "Цена детали составляет 9999 руб.",  # повторная галлюцинация
        ]
    )

    res = run_agent("Сколько стоит P-1042B?", llm, helper.as_dict())

    assert res.refused is True
    assert "9999" not in res.answer
    assert res.answer == "В базе знаний не найдено."


def test_run_agent_пробрасывает_отказ_базы_знаний():
    """Проверяет, что при отказе поиска по базе знаний (refused=True) агент возвращает честный отказ."""
    refused_search = {"answer": "В базе знаний не найдено.", "facts": [], "sources": [], "refused": True}
    helper = MockToolsHelper(search_knowledge=refused_search)
    llm = FakeLLM(
        [
            call("search_knowledge", question="Что означает ошибка E-17?"),
            "В базе знаний не найдено.",
        ]
    )

    res = run_agent("Что означает ошибка E-17 на AR-210?", llm, helper.as_dict())

    assert res.refused is True
    assert res.answer == "В базе знаний не найдено."
