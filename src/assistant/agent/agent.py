"""Цикл агента. Требования FR-7, FR-8, FR-9 и FR-10."""

import json
import re
from collections.abc import Callable

from assistant.agent.tools import TOOL_SCHEMAS
from assistant.infra.erp_client import ErpUnavailable
from assistant.infra.grounding import code_type, find_codes, normalize_code
from assistant.infra.llm import LLMClient, tool_message
from assistant.infra.schemas import AgentResult, ToolStep

_NUMBER = r"(?<![\w-])(?:\d{1,3}(?:[   ]\d{3})+|\d+)(?![\w-])"
_WITH_UNIT = re.compile(rf"({_NUMBER})\s*(руб|₽|шт)")
_STANDALONE_INT = re.compile(r"(?<![A-Za-zА-Яа-яЁё-])\b\d+\b(?!-)")

AGENT_SYSTEM_PROMPT = (
    "Ты ассистент сервисной службы компании «ПолярТех». Ты отвечаешь ТОЛЬКО по фактам из "
    "инструментов базы знаний и учётной системы (ERP).\n"
    "Правила выбора инструментов:\n"
    "1. `search_knowledge(question)`: вызывай для вопросов о моделях (AR-xxx, BZ-xxx, GS-xxx), "
    "кодах ошибок (E-xx), узлах, деталях (P-xxxx), их заменах, поставщиках и регламентах ремонта (SP-xxx). "
    "В аргументе `question` обязательно передавай точные коды и названия узлов из вопроса.\n"
    "2. `summarize_topic(question)`: вызывай для обзорных вопросов по линейкам и всему корпусу "
    "(какой узел чаще всего отказывает, у какой модели больше отказов, какие детали линейки сняты).\n"
    "3. `check_stock(part_id, warehouse)` и `get_price(part_id)`: вызывай для проверки остатка и цены "
    "в ERP, передавая актуальную (с учётом замен!) деталь. Для `get_price(part_id)` склад НЕ нужен — "
    "если пользователь спрашивает цену («сколько стоит»), вызывай `get_price` сразу после определения детали.\n"
    "4. `create_service_order(part_id, warehouse, qty, model)`: если пользователь просит оформить или "
    "создать заказ и известны актуальная деталь, модель, склад и количество из вопроса, обязательно вызови "
    "`create_service_order` (система сама запросит подтверждение у диспетчера).\n"
    "В финальном ответе обязательно указывай точные коды (P-xxxx, SP-xxx, BZ-xxx), названия, цены и остатки "
    "из результатов инструментов. Никогда не выдумывай числа, цены, остатки и коды деталей."
)


def _digits(raw: str) -> str:
    return re.sub(r"\D", "", raw)


def _find_discrepancies(
    answer: str,
    question: str,
    allowed_codes: set[str],
    allowed_numbers: set[str],
) -> list[str]:
    asked_codes = set(find_codes(question))
    invented: list[str] = []

    for code in find_codes(answer):
        if code not in allowed_codes and code not in asked_codes:
            invented.append(code)

    for raw, unit in _WITH_UNIT.findall(answer):
        d = _digits(raw)
        if d not in allowed_numbers:
            invented.append(f"{d} {unit}")

    return invented


def _normalize_call_args(raw_args: dict) -> dict:
    args = dict(raw_args)
    if isinstance(args.get("part_id"), str):
        norm_part = normalize_code(args["part_id"])
        if norm_part and code_type(norm_part) == "Part":
            args["part_id"] = norm_part
    if isinstance(args.get("model"), str):
        norm_model = normalize_code(args["model"])
        if norm_model and code_type(norm_model) == "Model":
            args["model"] = norm_model
    return args


def run_agent(
    question: str,
    llm: LLMClient,
    tools: dict[str, Callable[..., dict]],
    *,
    max_steps: int = 6,
    confirm: bool = False,
) -> AgentResult:
    """Ведёт диалог с моделью в цикле «рассуждение, вызов инструмента, наблюдение».

    Модель получает `TOOL_SCHEMAS` через `llm.chat(..., tools=...)`. Каждый вызов записывается
    в `steps` как `ToolStep`. Агент сам проверяет номер детали в аргументах (он должен встречаться
    в вопросе или в результатах прошлых инструментов), количество в заказе (должно быть названо
    пользователем) и повторные вызовы. При `ErpUnavailable` вызов повторяется до двух раз.
    Заказ создаётся только при `confirm=True`, иначе агент возвращает `needs_confirmation=True`
    и `pending_action`. Перед выдачей ответа коды, цены и остатки сверяются с вопросом
    и результатами инструментов.
    """
    messages: list[dict] = [
        {"role": "system", "content": AGENT_SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    steps: list[ToolStep] = []
    tool_cache: dict[tuple[str, str], dict] = {}
    sources: set[str] = set()

    known_parts: set[str] = {c for c in find_codes(question) if code_type(c) == "Part"}
    all_known_codes: set[str] = set(find_codes(question))
    allowed_numbers: set[str] = set()
    question_numbers: set[str] = set(_STANDALONE_INT.findall(question))

    kb_refused_any = False
    erp_not_found_any = False
    has_positive_evidence = False
    executed_tools_count = 0
    max_turns = max_steps + 8

    for _ in range(max_turns):
        response = llm.chat(messages, tools=TOOL_SCHEMAS)
        if not response.tool_calls:
            messages.append(response.as_message())
            break

        messages.append(response.as_message())

        for call in response.tool_calls:
            if executed_tools_count >= max_steps:
                err_msg = "Достигнут лимит шагов вызова инструментов (max_steps)."
                messages.append(tool_message(call, {"error": err_msg}))
                continue

            if call.name not in tools:
                err_msg = f"Неизвестный инструмент {call.name}."
                steps.append(ToolStep(tool=call.name, args=call.arguments, result=None, error=err_msg))
                messages.append(tool_message(call, {"error": err_msg}))
                continue

            if "_raw" in call.arguments:
                err_msg = f"Некорректные аргументы инструмента: {call.arguments['_raw']}"
                steps.append(ToolStep(tool=call.name, args=call.arguments, result=None, error=err_msg))
                messages.append(tool_message(call, {"error": err_msg}))
                continue

            args = _normalize_call_args(call.arguments)

            part_in_args = args.get("part_id")
            if part_in_args:
                norm_part = normalize_code(part_in_args) if isinstance(part_in_args, str) else None
                if not norm_part or norm_part not in known_parts:
                    err_msg = (
                        f"Номер детали {part_in_args} не подтверждён контекстом. "
                        "Сначала вызовите search_knowledge для поиска детали."
                    )
                    steps.append(ToolStep(tool=call.name, args=args, result=None, error=err_msg))
                    messages.append(tool_message(call, {"error": err_msg}))
                    continue

            if call.name == "create_service_order":
                qty = args.get("qty")
                if qty is None or isinstance(qty, bool) or not isinstance(qty, int) or str(qty) not in question_numbers:
                    err_msg = "Количество деталей не указано пользователем в вопросе. Уточните количество."
                    steps.append(ToolStep(tool=call.name, args=args, result=None, error=err_msg))
                    messages.append(tool_message(call, {"error": err_msg}))
                    continue

                if not confirm:
                    return AgentResult(
                        answer=(
                            f"Требуется подтверждение диспетчера для заказа детали {args.get('part_id', '')} "
                            f"(модель {args.get('model', '')}, склад {args.get('warehouse', '')}, "
                            f"количество {qty})."
                        ),
                        steps=steps,
                        sources=sorted(sources),
                        refused=False,
                        needs_confirmation=True,
                        pending_action={"tool": call.name, "args": args},
                    )

            cache_key = (call.name, json.dumps(args, sort_keys=True, ensure_ascii=False))
            if cache_key in tool_cache:
                cached_res = tool_cache[cache_key]
                steps.append(ToolStep(tool=call.name, args=args, result=cached_res, error=None))
                messages.append(tool_message(call, cached_res))
                continue

            tool_fn = tools[call.name]
            result_dict = None
            exec_error = None

            for attempt in range(3):
                try:
                    result_dict = tool_fn(**args)
                    exec_error = None
                    break
                except ErpUnavailable as e:
                    exec_error = f"ERP недоступна: {e}"
                    if attempt == 2:
                        break
                except TypeError as e:
                    exec_error = f"Некорректные аргументы инструмента: {e}"
                    break

            if exec_error is not None:
                steps.append(ToolStep(tool=call.name, args=args, result=None, error=exec_error))
                messages.append(tool_message(call, {"error": exec_error}))
                continue

            executed_tools_count += 1
            step_error = (
                result_dict.get("error")
                if (isinstance(result_dict, dict) and "error" in result_dict)
                else None
            )
            steps.append(ToolStep(tool=call.name, args=args, result=result_dict, error=step_error))
            tool_cache[cache_key] = result_dict

            res_str = json.dumps(result_dict, ensure_ascii=False)
            for num in re.findall(r"\d+", res_str):
                allowed_numbers.add(num)

            for code in find_codes(res_str):
                all_known_codes.add(code)
                if code_type(code) == "Part":
                    known_parts.add(code)

            if isinstance(result_dict, dict):
                if call.name in ("search_knowledge", "summarize_topic"):
                    if result_dict.get("refused") is True:
                        kb_refused_any = True
                    else:
                        has_positive_evidence = True
                elif step_error is None:
                    has_positive_evidence = True
                elif isinstance(step_error, str) and step_error.endswith("не найдена"):
                    erp_not_found_any = True

                if "sources" in result_dict and isinstance(result_dict["sources"], list):
                    for s in result_dict["sources"]:
                        sources.add(s.split("#")[0])

            messages.append(tool_message(call, result_dict))

    if messages[-1]["role"] != "assistant":
        final_resp = llm.chat(messages)
        messages.append(final_resp.as_message())
        candidate_text = final_resp.content.strip()
    else:
        candidate_text = messages[-1]["content"].strip()

    if (kb_refused_any or erp_not_found_any) and not has_positive_evidence:
        return AgentResult(
            answer="В базе знаний не найдено.",
            steps=steps,
            sources=sorted(sources),
            refused=True,
        )

    discrepancies = _find_discrepancies(candidate_text, question, all_known_codes, allowed_numbers)
    if discrepancies:
        messages.append(
            {
                "role": "user",
                "content": (
                    f"В твоём ответе обнаружены неподтверждённые данные ({', '.join(discrepancies)}). "
                    "Исправь ответ, опираясь строго на факты из вопроса и результатов вызова инструментов. "
                    "Не используй вымышленные цены, остатки и номера деталей."
                ),
            }
        )
        correction_resp = llm.chat(messages)
        candidate_text = correction_resp.content.strip()
        second_check = _find_discrepancies(candidate_text, question, all_known_codes, allowed_numbers)
        if second_check:
            return AgentResult(
                answer="В базе знаний не найдено.",
                steps=steps,
                sources=sorted(sources),
                refused=True,
            )

    return AgentResult(
        answer=candidate_text,
        steps=steps,
        sources=sorted(sources),
        refused=False,
        needs_confirmation=False,
        pending_action=None,
    )
