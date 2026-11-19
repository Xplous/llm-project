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
        fontSize=15.5,
        leading=19,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=2 * mm,
    )

    meta_style = ParagraphStyle(
        "DocMeta",
        fontName="Arial",
        fontSize=8.2,
        leading=11.5,
        textColor=colors.HexColor("#475569"),
        spaceAfter=2.5 * mm,
    )

    h1_style = ParagraphStyle(
        "Heading1_Custom",
        fontName="Arial-Bold",
        fontSize=10.8,
        leading=13.5,
        textColor=colors.HexColor("#1e3a8a"),
        spaceBefore=2.8 * mm,
        spaceAfter=1.4 * mm,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        "Body_Custom",
        fontName="Arial",
        fontSize=7.9,
        leading=10.8,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=1.4 * mm,
    )

    caption_style = ParagraphStyle(
        "Caption_Custom",
        fontName="Arial-Italic",
        fontSize=7.4,
        leading=9.8,
        textColor=colors.HexColor("#475569"),
        alignment=1,
        spaceBefore=1 * mm,
        spaceAfter=1.8 * mm,
    )

    code_style = ParagraphStyle(
        "Code_Custom",
        fontName="Arial",
        fontSize=7.2,
        leading=9.6,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=1 * mm,
    )

    table_header_style = ParagraphStyle(
        "TableHeader",
        fontName="Arial-Bold",
        fontSize=6.9,
        leading=8.8,
        textColor=colors.white,
        alignment=1,
    )

    table_cell_style = ParagraphStyle(
        "TableCell",
        fontName="Arial",
        fontSize=6.8,
        leading=8.6,
        textColor=colors.HexColor("#1e293b"),
    )

    table_cell_bold = ParagraphStyle(
        "TableCellBold",
        fontName="Arial-Bold",
        fontSize=6.8,
        leading=8.6,
        textColor=colors.HexColor("#1e293b"),
    )

    table_cell_center = ParagraphStyle(
        "TableCellCenter",
        fontName="Arial",
        fontSize=6.8,
        leading=8.6,
        textColor=colors.HexColor("#1e293b"),
        alignment=1,
    )

    table_cell_center_bold = ParagraphStyle(
        "TableCellCenterBold",
        fontName="Arial-Bold",
        fontSize=6.8,
        leading=8.6,
        textColor=colors.HexColor("#1e293b"),
        alignment=1,
    )

    story = []

    # ==================== СТРАНИЦА 1: ЗАДАЧА, РЕШЕНИЕ И АРХИТЕКТУРА ====================
    story.append(Paragraph("Отчёт: Ассистент сервисной службы «ПолярТех»", title_style))
    story.append(
        Paragraph(
            "<b>Репозиторий:</b> "
            "<font color='#2563eb'><u>https://github.com/Xplous/llm-project</u></font> | "
            "<b>LLM:</b> qwen3:4b-instruct-2507-q4_K_M (Ollama, GPU RTX 4070 SUPER) | "
            "<b>Эмбеддинги:</b> bge-m3 | <b>Тег:</b> v1.0",
            meta_style,
        )
    )
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1e3a8a"), spaceAfter=2 * mm))

    story.append(Paragraph("1. Задача", h1_style))
    task_desc = (
        "Компания «ПолярТех» обслуживает коммерческое и промышленное холодильное оборудование "
        "(витрины, моноблоки, чиллеры). Диспетчер принимает вызовы с моделью оборудования и кодом ошибки "
        "(например, «AR-210, код E-17»). Цель ассистента — определить причину неисправности, регламент ремонта "
        "и актуальную деталь (с учётом цепочек замен <code>REPLACED_BY</code>), проверить остатки по 4 складам "
        "(Москва, Санкт-Петербург, Казань, Новосибирск) и цены в ERP, и подготовить сервисный заказ с обязательным "
        "подтверждением человеком."
    )
    story.append(Paragraph(task_desc, body_style))

    rag_err_desc = (
        "<b>Почему плоский RAG не справляется:</b> 1) На многошаговом вопросе <b>dev-06</b> "
        "<i>(«Какую деталь заказать при ошибке E-17 на AR-210?»)</i> плоский RAG возвращает снятую с производства "
        "деталь <code>P-1042</code> из руководства, не переходя по сервисному бюллетеню к актуальной замене "
        "<code>P-1042B</code>. 2) На оперативных вопросах <b>dev-17, dev-20</b> <i>(остатки и цены в ERP)</i> "
        "плоский RAG получает точность <b>0.00</b>, так как динамические данные ERP отсутствуют в документах."
    )
    story.append(Paragraph(rag_err_desc, body_style))

    story.append(Paragraph("2. Архитектура решения и ReAct-конвейер", h1_style))
    sol_desc = (
        "Система объединяет три взаимодействующих контура (требования FR-1 — FR-10):<br/>"
        "• <b>Извлечение и Граф знаний (FR-1, FR-2):</b> <code>extraction.py</code> извлекает сущности и связи по "
        "JSON Schema (<code>max_tokens=4096</code>, 4 синтетических примера без утечки <code>gold_dev.json</code>) "
        "с заземлением кодов (<code>find_codes</code>) и словаря (<code>canonical_name</code>). "
        "<code>graph_builder.py</code> строит <code>nx.DiGraph</code> (118 узлов, 279 рёбер), фиксируя источники "
        "на обоих концах ребра и разрешая конфликты <code>REPLACED_BY</code> по весу.<br/>"
        "• <b>Сообщества и Поиск (FR-3, FR-4, FR-5):</b> Кластеризация Лувена (<code>seed=7</code>, 8 сообществ) "
        "с детерминированным подсчётом статистик по линейкам. <code>local_search</code> ищет пути длиной ≤ 3 "
        "между опорными узлами, автоматически разворачивает цепочки <code>REPLACED_BY</code> + "
        "<code>SUPPLIED_BY</code>/<code>IS_A</code> и мгновенно отказывает при неизвестном коде. "
        "<code>global_search</code> выполняет Map-Reduce (<code>MAP_SCHEMA</code>) по сводкам сообществ.<br/>"
        "• <b>Инструменты и Агент (FR-6 — FR-10):</b> 5 типизированных инструментов ERP/БЗ, ReAct-цикл "
        "(<code>max_steps=6</code>), проверка заземления деталей и чисел, до 3 попыток при <code>ErpUnavailable</code> "
        "и перехват <code>create_service_order</code> при <code>confirm=False</code> в <code>pending_action</code>."
    )
    story.append(Paragraph(sol_desc, body_style))

    if Path("figures/architecture_diagram.png").exists():
        story.append(Image("figures/architecture_diagram.png", width=168 * mm, height=79 * mm))
        caption_1 = "Рис. 1. Архитектура системы «ПолярТех»: ReAct-агент, граф знаний, ERP и шлюз безопасности"
        story.append(Paragraph(caption_1, caption_style))

    story.append(PageBreak())

    # ==================== СТРАНИЦА 2: РЕЗУЛЬТАТЫ И БЕНЧМАРК ====================
    story.append(Paragraph("3. Результаты и сравнительный бенчмарк", h1_style))
    story.append(
        Paragraph(
            "Оценка 4 режимов на 24 вопросах <code>questions_dev.jsonl</code> "
            "(<code>temperature=0</code>, <code>seed=7</code>, чистый кеш <code>artifacts/llm_cache/</code>):",
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
            Paragraph("<b>0.792 (19/24)</b>", table_cell_center_bold),
            Paragraph("0.417 (10/24)", table_cell_center_bold),
            Paragraph("<b>0.917 (22/24)</b>", table_cell_center_bold),
        ],
        [
            Paragraph("• Вопросы local (5)", table_cell_style),
            Paragraph("1.000 (5/5)", table_cell_center),
            Paragraph("<b>1.000 (5/5)</b>", table_cell_center_bold),
            Paragraph("0.800 (4/5)", table_cell_center),
            Paragraph("<b>1.000 (5/5)</b>", table_cell_center_bold),
        ],
        [
            Paragraph("• Вопросы multihop (7)", table_cell_style),
            Paragraph("0.571 (4/7)", table_cell_center),
            Paragraph("<b>1.000 (7/7)</b>", table_cell_center_bold),
            Paragraph("0.143 (1/7)", table_cell_center),
            Paragraph("<b>1.000 (7/7)</b>", table_cell_center_bold),
        ],
        [
            Paragraph("• Вопросы global (4)", table_cell_style),
            Paragraph("0.000 (0/4)", table_cell_center),
            Paragraph("<b>1.000 (4/4)</b>", table_cell_center_bold),
            Paragraph("0.500 (2/4)", table_cell_center),
            Paragraph("<b>0.750 (3/4)</b>", table_cell_center_bold),
        ],
        [
            Paragraph("• Вопросы tool (5)", table_cell_style),
            Paragraph("0.000 (0/5)", table_cell_center),
            Paragraph("0.000 (0/5)", table_cell_center),
            Paragraph("0.000 (0/5)", table_cell_center),
            Paragraph("<b>0.800 (4/5)</b>", table_cell_center_bold),
        ],
        [
            Paragraph("• Вопросы refusal (3)", table_cell_style),
            Paragraph("1.000 (3/3)", table_cell_center),
            Paragraph("<b>1.000 (3/3)</b>", table_cell_center_bold),
            Paragraph("<b>1.000 (3/3)</b>", table_cell_center_bold),
            Paragraph("<b>1.000 (3/3)</b>", table_cell_center_bold),
        ],
        [
            Paragraph("<b>Выдуманные факты (Fabricated)</b>", table_cell_bold),
            Paragraph("<b>0.000</b>", table_cell_center_bold),
            Paragraph("0.042*", table_cell_center),
            Paragraph("0.042", table_cell_center),
            Paragraph("0.042", table_cell_center),
        ],
        [
            Paragraph("Полнота источников (Source Recall)", table_cell_style),
            Paragraph("0.856", table_cell_center),
            Paragraph("<b>1.000</b>", table_cell_center_bold),
            Paragraph("0.719", table_cell_center),
            Paragraph("<b>1.000</b>", table_cell_center_bold),
        ],
        [
            Paragraph("Отклонённые вызовы инструментов", table_cell_style),
            Paragraph("—", table_cell_center),
            Paragraph("—", table_cell_center),
            Paragraph("—", table_cell_center),
            Paragraph("<b>0.032</b>", table_cell_center_bold),
        ],
        [
            Paragraph("<b>Вызовов модели на вопрос</b>", table_cell_bold),
            Paragraph("1.00", table_cell_center),
            Paragraph("<b>0.88</b>", table_cell_center_bold),
            Paragraph("7.67", table_cell_center),
            Paragraph("4.83", table_cell_center),
        ],
        [
            Paragraph("<b>Токенов на вопрос</b>", table_cell_bold),
            Paragraph("1356.7", table_cell_center),
            Paragraph("<b>1113.5</b>", table_cell_center_bold),
            Paragraph("3887.9", table_cell_center),
            Paragraph("5130.4", table_cell_center),
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
        story.append(Image("figures/benchmark_comparison.png", width=168 * mm, height=71 * mm))
        caption_2 = "Рис. 2. Сравнение точности по типам вопросов и удельной стоимости режимов (в токенах на вопрос)"
        story.append(Paragraph(caption_2, caption_style))

    stats_desc = (
        "<b>Качество извлечения на эталоне (<code>eval_extraction.json</code>, 16 документов):</b> "
        "Связи — Precision <b>1.000</b>, Recall <b>1.000</b> (161/161). "
        "Сущности — Precision <b>1.000</b>, Recall <b>1.000</b> (165/165). "
        "Отброшено проверками заземления: <b>0</b>.<br/>"
        "<b>Параметры графа и индексации (<code>index_stats.json</code>):</b> 80 документов (92 чанка), "
        "<b>118</b> узлов, <b>279</b> рёбер, <b>8</b> сообществ, 0 отброшено, 0 конфликтов. "
        "Затраты LLM: 100 вызовов (20 из кеша), 228 614 prompt-токенов, 40 812 completion-токенов."
    )
    story.append(Paragraph(stats_desc, body_style))

    story.append(PageBreak())

    # ==================== СТРАНИЦА 3: СРАВНЕНИЕ ГРАФА И ПЛОСКОГО RAG, ОШИБКИ ====================
    story.append(Paragraph("4. Где граф помогает и где уступает (Разбор двух примеров)", h1_style))
    ex1_text = (
        "<b>Пример 1 (Граф и Агент выигрывают):</b> Вопрос <b>dev-06 / dev-17</b> <i>(«Ошибка E-17 на AR-210. "
        "Какую деталь заказать, есть ли она в Казани и сколько стоит?»)</i>. Плоский RAG останавливается на "
        "устаревшей детали <code>P-1042</code> и лишён доступа к ERP. Граф находит путь "
        "<code>AR-210 -> P-1042 -> пусковое реле <- E-17</code>, разворачивает цепочку "
        "<code>P-1042 -> P-1042B -> ХолодКомплект</code>, а агент запрашивает ERP (3 шт., 2630 руб.). "
        "На вопросах отказа (<b>dev-22..24</b>) граф отказывает за <b>0 вызовов LLM</b> против 1357 токенов у Flat RAG."
    )
    story.append(Paragraph(ex1_text, body_style))

    ex2_text = (
        "<b>Пример 2 (Где граф уступает по стоимости или точности):</b> На простых однохоповых вопросах "
        "<b>dev-01..05</b> (<code>local</code>) плоский RAG даёт те же <b>100% (5/5)</b> за 1 вызов без "
        "затрат на индексацию графа, тогда как Агент расходует в среднем 4.83 вызова (5130 токенов). "
        "На обзорном вопросе <b>dev-14</b> <i>(«Какой узел чаще всего отказывает в линейке Гольфстрим?»)</i> "
        "маршрутизация через <code>summarize_topic</code> (Map-Reduce) привела к путанице модели-лидера "
        "(<code>GS-510</code>) с узлом-лидером (<code>циркуляционный насос</code>)."
    )
    story.append(Paragraph(ex2_text, body_style))

    if Path("figures/subgraph_topology.png").exists():
        story.append(Image("figures/subgraph_topology.png", width=168 * mm, height=79 * mm))
        caption_3 = "Рис. 3. Фрагмент графа знаний вокруг AR-210: обход пути ≤ 3 и разворачивание цепочки REPLACED_BY"
        story.append(Paragraph(caption_3, caption_style))

    story.append(Paragraph("5. Анализ ошибок системы и оптимизация", h1_style))
    err_text = (
        "Исследованы ошибки на всех трёх этапах конвейера:<br/>"
        "1. <b>Извлечение (<code>extraction.py</code>):</b> Лимит <code>max_tokens=1024</code> усекал JSON "
        "руководств (Recall 0.329), а 1-пунктовый пример приводил к извлечению только первой детали на 5 из 12 "
        "моделей. Увеличение лимита до 4096 и добавление 2-го пункта в синтетический пример подняли "
        "качество до <b>Precision 1.000 / Recall 1.000</b> (279 рёбер).<br/>"
        "2. <b>Сообщества и поиск (<code>communities.py</code>, <code>search.py</code>):</b> Разделение промпта "
        "сводок для сообществ с линейками и без них убрало шум, но на <b>dev-14</b> <code>summarize_topic</code> "
        "спутал модель-лидер <code>GS-510</code> с узлом-лидером. В режиме <code>local</code> на <b>dev-21</b> "
        "повтор «2 шт» из вопроса дал 1 ложное срабатывание метрики <code>fabricated</code> (0.042).<br/>"
        "3. <b>Агент и инструменты (<code>agent.py</code>):</b> На <b>dev-21</b> модель нашла <code>P-2054C</code>, "
        "проверила склад и цену, но вместо <code>create_service_order</code> написала текст с неподтверждённой "
        "суммой — барьер <code>_find_discrepancies</code> безопасно перевёл ответ в отказ. На <b>dev-12</b> "
        "модель ошиблась в коде регламента (<code>SP-205</code> вместо <code>SP-105</code>, 1/24 = 0.042)."
    )
    story.append(Paragraph(err_text, body_style))

    sub_headers = [
        Paragraph("Параметр извлечения", table_header_style),
        Paragraph("max_tokens=1024", table_header_style),
        Paragraph("4096 + 1 пример", table_header_style),
        Paragraph("4096 + 4 синтет. примера", table_header_style),
    ]
    sub_data = [
        sub_headers,
        [
            Paragraph("Связи: Precision / Recall", table_cell_bold),
            Paragraph("1.000 / 0.329", table_cell_center),
            Paragraph("1.000 / 0.590", table_cell_center),
            Paragraph("<b>1.000 / 1.000</b>", table_cell_center_bold),
        ],
        [
            Paragraph("Число рёбер графа", table_cell_bold),
            Paragraph("50 рёбер", table_cell_center),
            Paragraph("125 рёбер", table_cell_center),
            Paragraph("<b>279 рёбер</b>", table_cell_center_bold),
        ],
        [
            Paragraph("Отброшено (dropped, эталон)", table_cell_bold),
            Paragraph("12", table_cell_center),
            Paragraph("38", table_cell_center),
            Paragraph("<b>0</b>", table_cell_center_bold),
        ],
    ]
    sub_table = Table(sub_data, colWidths=[48 * mm, 36 * mm, 40 * mm, 46 * mm])
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
        "• <b>Остановка перед созданием заказа (FR-9):</b> При <code>confirm=False</code> вызов "
        "<code>create_service_order</code> перехватывается до обращения к ERP и не записывается в выполненные шаги: "
        "агент возвращает <code>needs_confirmation=True</code> и <code>pending_action</code>. Заказ создаётся "
        "только при явном флаге <code>--confirm</code>.<br/>"
        "• <b>Валидация аргументов (FR-7, FR-10):</b> Код детали должен быть в вопросе или результатах "
        "<code>search_knowledge</code>; количество <code>qty</code> — в вопросе; склад — из 4 допустимых "
        "(Москва, Санкт-Петербург, Казань, Новосибирск).<br/>"
        "• <b>Отказоустойчивость ERP:</b> При сбоях <code>ErpUnavailable</code> выполняются до 3 попыток; "
        "система строго разграничивает «нет данных» и «остаток 0»."
    )
    story.append(Paragraph(safe_text, body_style))

    if Path("figures/safety_flowchart.png").exists():
        story.append(Image("figures/safety_flowchart.png", width=168 * mm, height=69 * mm))
        caption_4 = "Рис. 4. Блок-схема барьеров безопасности и шлюза Human-in-the-Loop при выполнении операций"
        story.append(Paragraph(caption_4, caption_style))

    trace_text = (
        "<b>Реальная трассировка агента из <code>eval_agent.json</code> (dev-17) и шлюз подтверждения:</b><br/>"
        "<font color='#0f172a'><code>"
        "1. search_knowledge({'question': 'Ошибка E-17 на AR-210'}) -> пусковое реле, замена P-1042 -> P-1042B<br/>"
        "2. check_stock({'part_id': 'P-1042B', 'warehouse': 'Казань'}) -> {'qty': 3, 'discontinued': False}<br/>"
        "3. get_price({'part_id': 'P-1042B'}) -> {'name': 'пусковое реле', 'price_rub': 2630}<br/>"
        "Ответ: «Заменить деталь P-1042B (пусковое реле). "
        "Склад: Казань, остаток: 3 шт., цена: 2630 руб.»<br/>"
        "При заказе (confirm=False): [Safety Gate] create_service_order -> needs_confirmation=True, pending_action"
        "</code></font>"
    )
    story.append(Paragraph(trace_text, code_style))
    story.append(Spacer(1, 1.5 * mm))

    story.append(Paragraph("7. Следующий шаг развития системы", h1_style))
    next_step_text = (
        "<b>Проверяемая гипотеза: Структурированный маршрутизатор заказов + типизация сущностей в Map-Reduce.</b><br/>"
        "1) Подсказывать модели вызов <code>create_service_order</code>, когда в запросе есть «оформи заказ» и все "
        "4 аргумента подтверждены; 2) добавить в <code>MAP_SCHEMA</code> поле типа сущности (узел/модель/деталь), "
        "чтобы на шаге <code>reduce</code> не смешивать модель-лидер и узел-лидер (<code>dev-14</code>). "
        "<i>Проверка:</i> рост точности агента с 0.917 (22/24) до 1.000 (24/24) и снижение "
        "<code>fabricated_rate</code> до 0.000."
    )
    story.append(Paragraph(next_step_text, body_style))

    story.append(Paragraph("8. Вклад участников", h1_style))
    contrib_text = (
        "Проект выполнен индивидуально: проектирование промптов и заземления (<code>extraction.py</code>, "
        "<code>graph_builder.py</code>); кластеризация Лувена, статистика сообществ и режимы поиска "
        "(<code>communities.py</code>, <code>search.py</code>); ReAct-агент, инструменты ERP и шлюз подтверждения "
        "(<code>tools.py</code>, <code>agent.py</code>); 41 модульный тест (183 теста всего); запуск Ollama на GPU "
        "RTX 4070 SUPER, бенчмаркинг 4 режимов, анализ ошибок и оформление отчёта."
    )
    story.append(Paragraph(contrib_text, body_style))

    story.append(Paragraph("9. Использование ИИ-инструментов", h1_style))
    ai_text = (
        "Использовались ИИ-ассистенты кодирования (Antigravity / Gemini): 1) генерация модульных тестов граничных "
        "случаев (циклы замен, сбои ERP, перехват confirm=False); 2) диагностика усечения JSON и неполного "
        "извлечения списков руководств, рефакторинг промптов без утечки эталона; 3) подготовка скриптов "
        "генерации графиков и PDF. Все архитектурные решения, код 6 модулей, прогоны, метрики и целостность "
        "защищённой инфраструктуры проверены автором лично."
    )
    story.append(Paragraph(ai_text, body_style))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Отчёт успешно сформирован: {filename}")


if __name__ == "__main__":
    out_file = sys.argv[1] if len(sys.argv) > 1 else "REPORT.pdf"
    build_pdf(out_file)
