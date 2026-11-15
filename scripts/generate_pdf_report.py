"""Генератор REPORT.pdf из ReportLab с кириллицей, таблицами и графическими схемами."""

import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def register_fonts() -> None:
    font_paths = [
        ("Arial", "C:/Windows/Fonts/arial.ttf"),
        ("Arial-Bold", "C:/Windows/Fonts/arialbd.ttf"),
        ("Arial-Italic", "C:/Windows/Fonts/ariali.ttf"),
    ]
    registered = False
    for name, path in font_paths:
        if Path(path).exists():
            pdfmetrics.registerFont(TTFont(name, path))
            registered = True

    if not registered:
        dejavu = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
        if dejavu.exists():
            pdfmetrics.registerFont(TTFont("Arial", str(dejavu)))
            pdfmetrics.registerFont(TTFont("Arial-Bold", str(dejavu)))
            pdfmetrics.registerFont(TTFont("Arial-Italic", str(dejavu)))
        else:
            raise RuntimeError("Не найден кириллический шрифт TTF")


class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self) -> None:
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count: int) -> None:
        self.saveState()
        self.setFont("Arial", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        self.drawString(
            20 * mm,
            285 * mm,
            "ПолярТех — Ассистент сервисной службы | Итоговый отчёт (ITMO LLM Project)",
        )
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(20 * mm, 282 * mm, 190 * mm, 282 * mm)

        text = f"Стр. {self._pageNumber} из {page_count}"
        self.drawRightString(190 * mm, 12 * mm, text)
        self.drawString(
            20 * mm,
            12 * mm,
            "Репозиторий: https://github.com/Xplous/llm-project | Версия v1.0",
        )
        self.line(20 * mm, 16 * mm, 190 * mm, 16 * mm)
        self.restoreState()


def build_pdf(filename: str = "REPORT.pdf") -> None:
    register_fonts()

    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    title_style = ParagraphStyle(
        "DocTitle",
        fontName="Arial-Bold",
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=2 * mm,
    )

    meta_style = ParagraphStyle(
        "DocMeta",
        fontName="Arial",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#475569"),
        spaceAfter=2.5 * mm,
    )

    h1_style = ParagraphStyle(
        "Heading1_Custom",
        fontName="Arial-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#1e3a8a"),
        spaceBefore=3 * mm,
        spaceAfter=1.5 * mm,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        "Body_Custom",
        fontName="Arial",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=1.5 * mm,
    )

    caption_style = ParagraphStyle(
        "Caption_Custom",
        fontName="Arial-Italic",
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#475569"),
        alignment=1,
        spaceBefore=1 * mm,
        spaceAfter=2 * mm,
    )

    code_style = ParagraphStyle(
        "Code_Custom",
        fontName="Arial",
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=1 * mm,
    )

    table_header_style = ParagraphStyle(
        "TableHeader",
        fontName="Arial-Bold",
        fontSize=7,
        leading=9,
        textColor=colors.white,
        alignment=1,
    )

    table_cell_style = ParagraphStyle(
        "TableCell",
        fontName="Arial",
        fontSize=6.8,
        leading=8.8,
        textColor=colors.HexColor("#1e293b"),
    )

    table_cell_bold = ParagraphStyle(
        "TableCellBold",
        fontName="Arial-Bold",
        fontSize=6.8,
        leading=8.8,
        textColor=colors.HexColor("#1e293b"),
    )

    table_cell_center = ParagraphStyle(
        "TableCellCenter",
        fontName="Arial",
        fontSize=6.8,
        leading=8.8,
        textColor=colors.HexColor("#1e293b"),
        alignment=1,
    )

    table_cell_center_bold = ParagraphStyle(
        "TableCellCenterBold",
        fontName="Arial-Bold",
        fontSize=6.8,
        leading=8.8,
        textColor=colors.HexColor("#1e293b"),
        alignment=1,
    )

    story = []

    # ==================== СТРАНИЦА 1: ЗАДАЧА, РЕШЕНИЕ И АРХИТЕКТУРА ====================
    story.append(Paragraph("Отчёт: Ассистент сервисной службы «ПолярТех»", title_style))
    story.append(
        Paragraph(
            "<b>Репозиторий проекта:</b> "
            "<font color='#2563eb'><u>https://github.com/Xplous/llm-project</u></font> | "
            "<b>Модель:</b> qwen3:4b-instruct-2507-q4_K_M (Ollama, GPU RTX 4070 SUPER) | "
            "<b>Эмбеддинги:</b> bge-m3 | <b>Метка версии:</b> v1.0",
            meta_style,
        )
    )
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1e3a8a"), spaceAfter=2 * mm))

    # 1. Задача
    story.append(Paragraph("1. Задача", h1_style))
    task_desc = (
        "Компания «ПолярТех» обслуживает коммерческое и промышленное холодильное оборудование "
        "(витрины, бонеты, шкафы, моноблоки). Диспетчер сервисной службы принимает вызовы от клиентов, сообщающих "
        "модель оборудования и код возникшей ошибки (например, «AR-210, код E-17»). Цель ассистента — оперативно "
        "определить причину неисправности, регламент ремонта и деталь (с учётом снятия деталей с производства "
        "и их замен), проверить остатки и цены в учётной системе (ERP) и подготовить сервисный заказ "
        "с обязательным подтверждением человеком."
    )
    story.append(Paragraph(task_desc, body_style))

    rag_err_desc = (
        "<b>Пример ошибки плоского RAG:</b> На вопросе <b>dev-20</b> <i>(«Сколько штук детали P-1118B "
        "есть на складе в Казани?»)</i> плоский RAG показал точность <b>0.00</b>. Плоский RAG осуществляет поиск "
        "исключительно по статическому текстовому корпусу документов, где информация о динамических складских остатках "
        "и ценах отсутствует по определению. Он лишён доступа к API внешних систем, поэтому либо отказывается, "
        "либо галлюцинирует. В отличие от него, агентная система вызывает инструмент "
        "<code>check_stock(part_id='P-1118B', warehouse='Казань')</code> и выдаёт фактический остаток: 12 штук."
    )
    story.append(Paragraph(rag_err_desc, body_style))

    # 2. Решение
    story.append(Paragraph("2. Архитектура решения и ReAct-конвейер", h1_style))
    sol_desc = (
        "Система объединяет три взаимодействующих контура (требования FR-1 — FR-10):<br/>"
        "• <b>Извлечение и Граф знаний (FR-1, FR-2):</b> <code>extraction.py</code> извлекает сущности и связи по "
        "JSON Schema с валидацией заземления: коды сверяются с исходным чанком (<code>find_codes</code>), названия "
        "нормализуются по словарю (<code>canonical_name</code>). <code>graph_builder.py</code> объединяет результаты "
        "в <code>nx.DiGraph</code> с весами рёбер. Взаимные замены <code>REPLACED_BY</code> разрешаются в пользу "
        "ребра с большим весом.<br/>"
        "• <b>Сообщества и Поиск (FR-3, FR-4, FR-5):</b> Кластеризация графа методом Лувена (<code>seed=7</code>). "
        "Числовые статистики рёбер считаются детерминированно кодом. <code>local_search</code> ищет пути длиной ≤ 3 "
        "между опорными узлами с разворачиванием замен (отказ без вызова модели при отсутствии кодов). "
        "<code>global_search</code> выполняет Map-Reduce по сводкам сообществ.<br/>"
        "• <b>Инструменты и Агент (FR-6 — FR-10):</b> 5 типизированных инструментов, ReAct-цикл (лимит 6 шагов), "
        "проверка обоснованности деталей, 3 повтора при недоступности ERP (<code>ErpUnavailable</code>) и перехват "
        "создания заказов до подтверждения диспетчером."
    )
    story.append(Paragraph(sol_desc, body_style))

    if Path("figures/architecture_diagram.png").exists():
        story.append(Image("figures/architecture_diagram.png", width=170 * mm, height=72 * mm))
        caption_1 = "Рис. 1. Архитектура системы «ПолярТех»: ReAct-агент, граф знаний, ERP и шлюз безопасности"
        story.append(Paragraph(caption_1, caption_style))

    story.append(PageBreak())

    # ==================== СТРАНИЦА 2: РЕЗУЛЬТАТЫ И БЕНЧМАРК ====================
    story.append(Paragraph("3. Результаты и сравнительный бенчмарк", h1_style))
    story.append(
        Paragraph(
            "Оценка 4 режимов на 24 вопросах выборки (температура 0, seed=7, модель <code>qwen3:4b-instruct</code>):",
            body_style,
        )
    )

    headers = [
        Paragraph("Метрика", table_header_style),
        Paragraph("Baseline (Flat RAG)", table_header_style),
        Paragraph("Local (Graph)", table_header_style),
        Paragraph("Global (Graph)", table_header_style),
        Paragraph("Agent (Граф+ERP)", table_header_style),
    ]

    data = [
        headers,
        [
            Paragraph("<b>Общая точность (Accuracy)</b>", table_cell_bold),
            Paragraph("0.500 (12/24)", table_cell_center_bold),
            Paragraph("0.417 (10/24)", table_cell_center_bold),
            Paragraph("0.208 (5/24)", table_cell_center_bold),
            Paragraph("0.250 (6/24)", table_cell_center_bold),
        ],
        [
            Paragraph("• Вопросы local (5)", table_cell_style),
            Paragraph("1.000 (5/5)", table_cell_center),
            Paragraph("0.800 (4/5)", table_cell_center),
            Paragraph("0.600 (3/5)", table_cell_center),
            Paragraph("0.800 (4/5)", table_cell_center),
        ],
        [
            Paragraph("• Вопросы multihop (7)", table_cell_style),
            Paragraph("0.571 (4/7)", table_cell_center),
            Paragraph("0.143 (1/7)", table_cell_center),
            Paragraph("0.286 (2/7)", table_cell_center),
            Paragraph("0.143 (1/7)", table_cell_center),
        ],
        [
            Paragraph("• Вопросы global (4)", table_cell_style),
            Paragraph("0.000 (0/4)", table_cell_center),
            Paragraph("0.500 (2/4)", table_cell_center),
            Paragraph("0.000 (0/4)", table_cell_center),
            Paragraph("0.000 (0/4)", table_cell_center),
        ],
        [
            Paragraph("• Вопросы tool (5)", table_cell_style),
            Paragraph("0.000 (0/5)", table_cell_center),
            Paragraph("0.000 (0/5)", table_cell_center),
            Paragraph("0.000 (0/5)", table_cell_center),
            Paragraph("<b>0.200 (1/5)</b>", table_cell_center_bold),
        ],
        [
            Paragraph("• Вопросы refusal (3)", table_cell_style),
            Paragraph("1.000 (3/3)", table_cell_center),
            Paragraph("1.000 (3/3)", table_cell_center),
            Paragraph("0.000 (0/3)", table_cell_center),
            Paragraph("0.000 (0/3)", table_cell_center),
        ],
        [
            Paragraph("<b>Выдуманные факты (Fabricated)</b>", table_cell_bold),
            Paragraph("<b>0.000</b>", table_cell_center_bold),
            Paragraph("<b>0.000</b>", table_cell_center_bold),
            Paragraph("0.083", table_cell_center),
            Paragraph("<b>0.000</b>", table_cell_center_bold),
        ],
        [
            Paragraph("Полнота источников (Source Recall)", table_cell_style),
            Paragraph("0.856", table_cell_center),
            Paragraph("0.594", table_cell_center),
            Paragraph("<b>1.000</b>", table_cell_center_bold),
            Paragraph("0.531", table_cell_center),
        ],
        [
            Paragraph("Отклонённые вызовы инструментов", table_cell_style),
            Paragraph("—", table_cell_center),
            Paragraph("—", table_cell_center),
            Paragraph("—", table_cell_center),
            Paragraph("0.087", table_cell_center),
        ],
        [
            Paragraph("<b>Вызовов модели на вопрос</b>", table_cell_bold),
            Paragraph("1.00", table_cell_center),
            Paragraph("<b>0.63</b>", table_cell_center_bold),
            Paragraph("25.00", table_cell_center),
            Paragraph("7.58", table_cell_center),
        ],
        [
            Paragraph("<b>Токенов на вопрос</b>", table_cell_bold),
            Paragraph("1356.2", table_cell_center),
            Paragraph("<b>238.7</b>", table_cell_center_bold),
            Paragraph("16471.7", table_cell_center),
            Paragraph("5461.5", table_cell_center),
        ],
    ]

    col_widths = [44 * mm, 32 * mm, 32 * mm, 32 * mm, 34 * mm]
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("TOPPADDING", (0, 0), (-1, -1), 1.2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1.2),
            ]
        )
    )
    story.append(t)
    story.append(Spacer(1, 2 * mm))

    if Path("figures/benchmark_comparison.png").exists():
        story.append(Image("figures/benchmark_comparison.png", width=170 * mm, height=65 * mm))
        caption_2 = "Рис. 2. Сравнение точности по типам вопросов и удельной стоимости режимов (в токенах на вопрос)"
        story.append(Paragraph(caption_2, caption_style))

    stats_desc = (
        "<b>Качество извлечения на эталоне (`eval_extraction.json`):</b> Связи — Precision <b>1.000</b> (100%), "
        "Recall <b>0.590</b> (59%). Сущности — Precision <b>0.994</b>, Recall <b>0.976</b>. "
        "Отброшено проверками заземления: 38.<br/>"
        "<b>Параметры графа и стоимость индексации (`index_stats.json`):</b> 80 документов (92 чанка), "
        "<b>120</b> узлов, <b>125</b> рёбер, <b>24</b> сообщества, 0 конфликтов. Затраты LLM: 116 вызовов "
        "(31 из кеша), 82 648 prompt-токенов, 42 517 completion-токенов."
    )
    story.append(Paragraph(stats_desc, body_style))

    story.append(PageBreak())

    # ==================== СТРАНИЦА 3: СРАВНЕНИЕ ГРАФА И ПЛОСКОГО RAG, ОШИБКИ ====================
    story.append(Paragraph("4. Где граф помогает и где уступает (Разбор двух примеров)", h1_style))
    ex1_text = (
        "<b>Пример 1 (Граф и Агент выигрывают):</b> Вопрос <b>dev-20</b> <i>(«Сколько штук детали P-1118B "
        "есть на складе в Казани?»)</i>. Плоский RAG лишён доступа к ERP и терпит неудачу. Агент извлекает "
        "код, проверяет заземление и запрашивает ERP (12 шт.). Кроме того, на вопросах <b>dev-22 — dev-24</b> "
        "<code>local_search</code> детерминированно отказывает на уровне кода <b>с 0 вызовов модели и 0 токенов</b>, "
        "тогда как плоский RAG тратит свыше 1300 токенов на эмбеддинги и генерацию ответа."
    )
    story.append(Paragraph(ex1_text, body_style))

    ex2_text = (
        "<b>Пример 2 (Плоский RAG выигрывает):</b> Вопрос <b>dev-08</b> <i>(«Кто сейчас поставляет деталь "
        "узла «реле давления» для модели BZ-120?»)</i>. Поиск плоского RAG (<code>bge-m3</code>) находит чанк "
        "<code>manual_BZ-120.md</code>, где реле и поставщик указаны вместе, отвечая за 1 вызов. В графе знаний "
        "этот запрос требует многошаговой траектории (4 ребра): <code>BZ-120 -> P-1026 -> реле давления</code>, затем "
        "<code>P-1026 -> P-1026B -> ХолодКомплект</code>. Лимит поиска путей (≤ 3 хопов) отсёк конечного поставщика."
    )
    story.append(Paragraph(ex2_text, body_style))

    if Path("figures/subgraph_topology.png").exists():
        story.append(Image("figures/subgraph_topology.png", width=165 * mm, height=68 * mm))
        caption_3 = (
            "Рис. 3. Фрагмент графа знаний вокруг AR-210: цепочка актуальной замены и обрыв пути при max_hops ≤ 3"
        )
        story.append(Paragraph(caption_3, caption_style))

    story.append(Paragraph("5. Анализ ошибок системы и оптимизация", h1_style))
    err_text = (
        "Исследованы три ошибки на разных этапах конвейера:<br/>"
        "1. <b>Этап извлечения (Extraction):</b> При обработке руководств ответ модели усекался лимитом "
        "<code>max_tokens=1024</code>. JSON обрывался, чанк возвращал 0 сущностей. Увеличение до 4096 токенов "
        "подняло Recall связей с 0.33 до 0.59, а число рёбер графа — с 50 до 125.<br/>"
        "2. <b>Этап поиска (Search):</b> Ограничение путей (≤ 3 рёбер) в <code>local_search</code> приводило "
        "к потерям на вопросах <code>multihop</code> (точность 14.3% против 57.1% у Flat RAG).<br/>"
        "3. <b>Этап инструментов/генерации (Agent/Tools):</b> На вопросе <b>dev-21</b> агент связал ошибку E-20 "
        "с деталью P-1042 и её заменой P-1042B, проверил склад, но потратил оставшиеся шаги на повторные "
        "запросы в базу знаний вместо прямого вызова заказа, исчерпав лимит <code>max_steps=6</code>."
    )
    story.append(Paragraph(err_text, body_style))

    # Таблица было/стало
    sub_headers = [
        Paragraph("Параметр извлечения", table_header_style),
        Paragraph("До исправления (max_tokens=1024)", table_header_style),
        Paragraph("После исправления (max_tokens=4096)", table_header_style),
        Paragraph("Дельта эффекта", table_header_style),
    ]
    sub_data = [
        sub_headers,
        [
            Paragraph("Полнота связей (Recall)", table_cell_bold),
            Paragraph("0.329 (33%)", table_cell_center),
            Paragraph("0.590 (59%)", table_cell_center_bold),
            Paragraph("+79.3% рост", table_cell_center_bold),
        ],
        [
            Paragraph("Число рёбер графа", table_cell_bold),
            Paragraph("50 рёбер", table_cell_center),
            Paragraph("125 рёбер", table_cell_center_bold),
            Paragraph("в 2.5 раза больше", table_cell_center_bold),
        ],
        [
            Paragraph("Число узлов графа", table_cell_bold),
            Paragraph("79 узлов", table_cell_center),
            Paragraph("120 узлов", table_cell_center_bold),
            Paragraph("+51.9% узлов", table_cell_center_bold),
        ],
    ]
    sub_table = Table(sub_data, colWidths=[48 * mm, 42 * mm, 45 * mm, 35 * mm])
    sub_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ]
        )
    )
    story.append(sub_table)

    story.append(PageBreak())

    # ==================== СТРАНИЦА 4: БЕЗОПАСНОСТЬ, СЛЕДУЮЩИЙ ШАГ И ВКЛАД ====================
    story.append(Paragraph("6. Границы системы и безопасность (FR-9, FR-10)", h1_style))
    safe_text = (
        "Система реализует строгие архитектурные барьеры безопасности (Human-in-the-Loop):<br/>"
        "• <b>Остановка перед созданием заказа:</b> Инструмент <code>create_service_order</code> мутирует "
        "данные ERP. При <code>confirm=False</code> вызов перехватывается: агент возвращает "
        "<code>needs_confirmation=True</code> и объект <code>pending_action</code> с параметрами, требуя "
        "подтверждения оператора. Создание заказа выполняется только при явном флаге <code>--confirm</code>.<br/>"
        "• <b>Валидация деталей:</b> Агент запрещает передавать в инструменты номера деталей, которые "
        "не упоминались в вопросе и не были найдены через <code>search_knowledge</code>.<br/>"
        "• <b>Отказоустойчивость ERP:</b> При сбоях сети (<code>ErpUnavailable</code>) выполняются 3 повтора. "
        "Ответы системы строго разграничивают «нет данных» и «остаток 0»."
    )
    story.append(Paragraph(safe_text, body_style))

    if Path("figures/safety_flowchart.png").exists():
        story.append(Image("figures/safety_flowchart.png", width=165 * mm, height=60 * mm))
        caption_4 = "Рис. 4. Блок-схема барьеров безопасности и шлюза Human-in-the-Loop при выполнении операций"
        story.append(Paragraph(caption_4, caption_style))

    # Врезка трассировки агента
    trace_text = (
        "<b>Пример трассировки ReAct-цикла на заказе (dev-21):</b><br/>"
        "<font color='#0f172a'><code>"
        "1. Tool: search_knowledge({'question': 'ошибка E-20 на BZ-120'}) -> узел 'пусковое реле', деталь P-1042<br/>"
        "2. Tool: search_knowledge({'question': 'замена P-1042'}) -> актуальная замена P-1042B<br/>"
        "3. Tool: check_stock({'part_id': 'P-1042B', 'warehouse': 'Москва'}) -> остаток: 8 шт.<br/>"
        "4. [Safety Gate] create_service_order -> confirm=False: перехват мутации, возврат pending_action<br/>"
        "Ответ диспетчеру: «Для витрины BZ-120 требуется деталь P-1042B (2 шт., склад Москва). Подтвердите заказ?»"
        "</code></font>"
    )
    story.append(Paragraph(trace_text, code_style))
    story.append(Spacer(1, 1.5 * mm))

    # 7. Следующий шаг
    story.append(Paragraph("7. Следующий шаг развития системы", h1_style))
    next_step_text = (
        "<b>Проверяемая гипотеза: Гибридный графо-векторный ретривер (Hybrid Subgraph RAG).</b><br/>"
        "Вместо поиска путей фиксированной длины предлагается: 1) находить 2–3 релевантных чанка плотным "
        "поиском (<code>bge-m3</code>); 2) использовать их сущности как центры подграфа; 3) расширять подграф "
        "на радиус 1 по рёбрам замен и поставщиков. <i>Проверка:</i> Точность на вопросах <code>multihop</code> "
        "должна вырасти с 14.3% до ≥ 60% при сохранении 0% галлюцинаций."
    )
    story.append(Paragraph(next_step_text, body_style))

    # 8. Вклад участников
    story.append(Paragraph("8. Вклад участников", h1_style))
    contrib_text = (
        "Проект выполнен в полном объёме индивидуально: проектирование схемы графа и онтологии; реализация "
        "модулей извлечения, графа, сообществ и поиска (Эпики 1 и 2); разработка ReAct-агента, инструментов ERP "
        "и подтверждения человеком (Эпик 3); написание 41 контрактного теста (183 теста в CI); запуск Ollama "
        "на GPU CUDA в Docker, бенчмаркинг 4 режимов и анализ результатов (Эпики 4 и 5)."
    )
    story.append(Paragraph(contrib_text, body_style))

    # 9. Использование ИИ-инструментов
    story.append(Paragraph("9. Использование ИИ-инструментов", h1_style))
    ai_text = (
        "Использовались ИИ-ассистенты (Antigravity / Gemini CLI): 1) генерация контрактных тестов граничных "
        "случаев (сбои ERP, зацикливание замен); 2) профилирование и отладка лимитов токенов при генерации JSON; "
        "3) настройка пайплайна GitHub Actions CI. Все алгоритмические решения проверены автором лично "
        "и защищаются индивидуально."
    )
    story.append(Paragraph(ai_text, body_style))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Отчёт успешно сформирован: {filename}")


if __name__ == "__main__":
    out_file = sys.argv[1] if len(sys.argv) > 1 else "REPORT.pdf"
    build_pdf(out_file)
