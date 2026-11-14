"""Генератор REPORT.pdf из ReportLab с поддержкой кириллицы и профессиональной вёрсткой."""

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
    KeepTogether,
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
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
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
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=22 * mm,
        bottomMargin=22 * mm,
    )

    title_style = ParagraphStyle(
        "DocTitle",
        fontName="Arial-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=3 * mm,
    )

    meta_style = ParagraphStyle(
        "DocMeta",
        fontName="Arial",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#475569"),
        spaceAfter=3 * mm,
    )

    h1_style = ParagraphStyle(
        "Heading1_Custom",
        fontName="Arial-Bold",
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#1e3a8a"),
        spaceBefore=4 * mm,
        spaceAfter=1.5 * mm,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        "Body_Custom",
        fontName="Arial",
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=1.5 * mm,
    )

    bullet_style = ParagraphStyle(
        "Bullet_Custom",
        fontName="Arial",
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#1e293b"),
        leftIndent=3 * mm,
        spaceAfter=1.2 * mm,
    )

    table_header_style = ParagraphStyle(
        "TableHeader",
        fontName="Arial-Bold",
        fontSize=7.5,
        leading=9.5,
        textColor=colors.white,
        alignment=1,
    )

    table_cell_style = ParagraphStyle(
        "TableCell",
        fontName="Arial",
        fontSize=7,
        leading=9,
        textColor=colors.HexColor("#1e293b"),
    )

    table_cell_bold = ParagraphStyle(
        "TableCellBold",
        fontName="Arial-Bold",
        fontSize=7,
        leading=9,
        textColor=colors.HexColor("#1e293b"),
    )

    table_cell_center = ParagraphStyle(
        "TableCellCenter",
        fontName="Arial",
        fontSize=7,
        leading=9,
        textColor=colors.HexColor("#1e293b"),
        alignment=1,
    )

    table_cell_center_bold = ParagraphStyle(
        "TableCellCenterBold",
        fontName="Arial-Bold",
        fontSize=7,
        leading=9,
        textColor=colors.HexColor("#1e293b"),
        alignment=1,
    )

    story = []

    story.append(Paragraph("Отчёт: Ассистент сервисной службы «ПолярТех»", title_style))
    story.append(
        Paragraph(
            "<b>Репозиторий проекта:</b> "
            "<font color='#2563eb'><u>https://github.com/Xplous/llm-project</u></font><br/>"
            "<b>Модель:</b> qwen3:4b-instruct-2507-q4_K_M (Ollama, GPU RTX 4070 SUPER) | "
            "<b>Эмбеддинги:</b> bge-m3 | <b>Метка версии:</b> v1.0",
            meta_style,
        )
    )
    story.append(HRFlowable(width="100%", thickness=1.2, color=colors.HexColor("#1e3a8a"), spaceAfter=2.5 * mm))

    # 1. Задача
    story.append(Paragraph("1. Задача", h1_style))
    story.append(
        Paragraph(
            "Компания «ПолярТех» обслуживает холодильное оборудование магазинов и складов (витрины, бонеты, шкафы). "
            "Диспетчер принимает звонки, сообщающие модель установки и код ошибки (например, «AR-210, код E-17»). "
            "Цель ассистента — оперативно определить причину сбоя, регламент ремонта и деталь по документации "
            "(с учётом снятия деталей с производства и их замен), проверить остатки и цены в ERP "
            "и подготовить заказ с подтверждением человеком.",
            body_style,
        )
    )
    story.append(
        Paragraph(
            "<b>Пример ошибки плоского RAG:</b> На вопросе <b>dev-20</b> <i>(«Сколько штук детали P-1118B "
            "есть на складе в Казани?»)</i> плоский RAG показал точность <b>0.00</b>. Плоский RAG ищет только "
            "по статическим текстам, где динамические остатки отсутствуют по определению. Не имея доступа "
            "к API учётной системы, он отказывается или галлюцинирует. Агент с графом вызывает инструмент "
            "<code>check_stock(part_id='P-1118B', warehouse='Казань')</code> и даёт точный ответ: 12 штук.",
            body_style,
        )
    )

    # 2. Решение
    story.append(Paragraph("2. Решение", h1_style))
    story.append(
        Paragraph(
            "Архитектура системы состоит из трёх подсистем, реализованных по требованиям FR-1 — FR-10:",
            body_style,
        )
    )
    story.append(
        Paragraph(
            "• <b>Извлечение и Граф знаний (FR-1, FR-2):</b> <code>extraction.py</code> извлекает сущности "
            "и связи по JSON Schema с заземлением: коды проверяются в исходном чанке (<code>find_codes</code>), "
            "названия нормализуются по словарю (<code>canonical_name</code>). Невалидные элементы отбрасываются "
            "(<code>dropped</code>). <code>graph_builder.py</code> собирает <code>nx.DiGraph</code> с весами рёбер. "
            "Взаимные замены <code>REPLACED_BY</code> разрешаются в пользу большего веса.",
            bullet_style,
        )
    )
    story.append(
        Paragraph(
            "• <b>Сообщества и Поиск (FR-3, FR-4, FR-5):</b> <code>communities.py</code> кластеризует граф "
            "алгоритмом Лувена (<code>seed=7</code>). Статистики рёбер считаются детерминированно кодом. "
            "<code>local_search</code> строит пути длиной ≤ 3 между опорными узлами с разворачиванием замен; "
            "при отсутствии кодов даёт отказ без LLM. <code>global_search</code> выполняет Map-Reduce по сводкам.",
            bullet_style,
        )
    )
    story.append(
        Paragraph(
            "• <b>Инструменты и ReAct-агент (FR-6 — FR-10):</b> <code>tools.py</code> предоставляет 5 типизированных "
            "инструментов. <code>agent.py</code> управляет циклом ReAct (до 6 шагов), валидирует номера деталей, "
            "делает до 3 повторов при <code>ErpUnavailable</code>, отсекает дубли и останавливается перед "
            "созданием заказа (<code>confirm=False</code>) до подтверждения оператором.",
            bullet_style,
        )
    )

    # 3. Результаты
    story.append(Paragraph("3. Результаты", h1_style))
    story.append(
        Paragraph(
            "Сравнение четырёх режимов на 24 вопросах выборки (температура 0, seed=7):",
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

    col_widths = [45 * mm, 31 * mm, 31 * mm, 31 * mm, 32 * mm]
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("TOPPADDING", (0, 0), (-1, -1), 1.8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1.8),
            ]
        )
    )

    story.append(KeepTogether([t, Spacer(1, 2 * mm)]))

    story.append(
        Paragraph(
            "<b>Качество извлечения на эталоне (eval_extraction.json):</b> Связи — Precision <b>1.000</b> (100%), "
            "Recall <b>0.590</b> (59%). Сущности — Precision <b>0.994</b>, Recall <b>0.976</b>. "
            "Отброшено проверками заземления: 38.<br/>"
            "<b>Параметры графа и стоимость индексации (index_stats.json):</b> 80 документов (92 чанка), "
            "<b>120</b> узлов, <b>125</b> рёбер, <b>24</b> сообщества, 0 конфликтов. Затраты LLM: 116 вызовов "
            "(31 из кеша), 82 648 prompt-токенов, 42 517 completion-токенов.",
            body_style,
        )
    )

    # 4. Где граф помогает и где уступает
    story.append(Paragraph("4. Где граф помогает и где уступает", h1_style))
    story.append(
        Paragraph(
            "<b>Пример 1 (Граф и Агент выигрывают):</b> Вопрос <b>dev-20</b> <i>(«Сколько штук детали P-1118B "
            "есть на складе в Казани?»)</i>. Плоский RAG не имеет доступа к ERP и ошибается. Агент извлекает "
            "код, проверяет заземление и запрашивает ERP (12 шт.). Кроме того, на вопросах <b>dev-22 — dev-24</b> "
            "<code>local_search</code> детерминированно отказывает на уровне кода "
            "<b>с 0 вызовов модели и 0 токенов</b>, "
            "тогда как плоский RAG тратит >1300 токенов на эмбеддинги и генерацию.",
            body_style,
        )
    )
    story.append(
        Paragraph(
            "<b>Пример 2 (Плоский RAG выигрывает):</b> Вопрос <b>dev-08</b> <i>(«Кто сейчас поставляет деталь "
            "узла «реле давления» для модели BZ-120?»)</i>. Семантический поиск плоского RAG находит чанк "
            "<code>manual_BZ-120.md</code>, где реле и поставщик указаны рядом, отвечая за 1 вызов. В графе "
            "запрос требует пути в 4 ребра (<code>BZ-120 -> P-1026 -> реле давления</code>, затем "
            "<code>P-1026 -> P-1026B -> ХолодКомплект</code>). Лимит путей (≤ 3 хопов) отсёк конечного поставщика.",
            body_style,
        )
    )

    # 5. Ошибки
    story.append(Paragraph("5. Анализ ошибок системы", h1_style))
    story.append(
        Paragraph(
            "Исследованы три ошибки на разных этапах конвейера:<br/>"
            "1. <b>Этап извлечения (Extraction):</b> При обработке руководств ответ модели усекался лимитом "
            "<code>max_tokens=1024</code>. JSON обрывался, чанк возвращал 0 сущностей. Увеличение до 4096 токенов "
            "подняло Recall связей с 0.33 до 0.59, а число рёбер графа — с 50 до 125.<br/>"
            "2. <b>Этап поиска (Search):</b> Ограничение путей (≤ 3 рёбер) в <code>local_search</code> приводило "
            "к потерям на вопросах <code>multihop</code> (точность 14.3% против 57.1% у Flat RAG).<br/>"
            "3. <b>Этап инструментов/генерации (Agent/Tools):</b> На вопросе <b>dev-21</b> агент связал ошибку E-20 "
            "с деталью P-1042 и её заменой P-1042B, проверил склад, но потратил оставшиеся шаги на повторные "
            "запросы в базу знаний вместо вызова заказа, исчерпав лимит <code>max_steps=6</code>.<br/>"
            "<b>Показатели надёжности:</b> Доля выдуманных фактов у Агента и Local — <b>0.000</b>. "
            "Отброшено связей при валидации — <b>38</b> на эталоне (175 на корпусе).",
            body_style,
        )
    )

    # 6. Границы системы
    story.append(Paragraph("6. Границы системы и безопасность (FR-9, FR-10)", h1_style))
    story.append(
        Paragraph(
            "Система реализует строгие архитектурные барьеры безопасности (Human-in-the-Loop):<br/>"
            "• <b>Остановка перед созданием заказа:</b> Инструмент <code>create_service_order</code> мутирует "
            "данные ERP. При <code>confirm=False</code> вызов перехватывается: агент возвращает "
            "<code>needs_confirmation=True</code> и объект <code>pending_action</code> с параметрами, требуя "
            "подтверждения оператора. Создание заказа выполняется только при явном флаге <code>--confirm</code>.<br/>"
            "• <b>Валидация деталей:</b> Агент запрещает передавать в инструменты номера деталей, которые "
            "не упоминались в вопросе и не были найдены через <code>search_knowledge</code>.<br/>"
            "• <b>Отказоустойчивость ERP:</b> При сбоях сети (<code>ErpUnavailable</code>) выполняются 3 повтора. "
            "Ответы системы строго разграничивают «нет данных» и «остаток 0».",
            body_style,
        )
    )

    # 7. Следующий шаг
    story.append(Paragraph("7. Следующий шаг развития системы", h1_style))
    story.append(
        Paragraph(
            "<b>Проверяемая гипотеза: Гибридный графо-векторный ретривер (Hybrid Subgraph RAG).</b><br/>"
            "Вместо поиска путей фиксированной длины предлагается: 1) находить 2–3 релевантных чанка плотным "
            "поиском (<code>bge-m3</code>); 2) использовать их сущности как центры подграфа; 3) расширять подграф "
            "на радиус 1 по рёбрам замен и поставщиков. <i>Проверка:</i> Точность на вопросах <code>multihop</code> "
            "должна вырасти с 14.3% до ≥ 60% при сохранении 0% галлюцинаций.",
            body_style,
        )
    )

    # 8. Вклад участников
    story.append(Paragraph("8. Вклад участников", h1_style))
    story.append(
        Paragraph(
            "Проект выполнен в полном объёме индивидуально: проектирование схемы графа и онтологии; реализация "
            "модулей извлечения, графа, сообществ и поиска (Эпики 1 и 2); разработка ReAct-агента, инструментов ERP "
            "и подтверждения человеком (Эпик 3); написание 41 контрактного теста (183 теста в CI); запуск Ollama "
            "на GPU CUDA в Docker, бенчмаркинг 4 режимов и анализ результатов (Эпики 4 и 5).",
            body_style,
        )
    )

    # 9. Использование ИИ-инструментов
    story.append(Paragraph("9. Использование ИИ-инструментов", h1_style))
    story.append(
        Paragraph(
            "Использовались ИИ-ассистенты (Antigravity / Gemini CLI): 1) генерация контрактных тестов граничных "
            "случаев (сбои ERP, зацикливание замен); 2) профилирование и отладка лимитов токенов при генерации JSON; "
            "3) настройка пайплайна GitHub Actions CI. Все алгоритмические решения проверены автором лично "
            "и защищаются индивидуально.",
            body_style,
        )
    )

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Отчёт успешно сформирован: {filename}")


if __name__ == "__main__":
    out_file = sys.argv[1] if len(sys.argv) > 1 else "REPORT.pdf"
    build_pdf(out_file)
