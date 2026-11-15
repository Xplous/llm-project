"""Скрипт генерации графических материалов для отчёта REPORT.pdf с академическим стилем."""

from pathlib import Path

import matplotlib.patches as patches
import matplotlib.pyplot as plt

FIGURES_DIR = Path("figures")
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

# Глобальные параметры стиля: аккуратные шрифты, нейтральные цвета
plt.rcParams.update({
    "font.sans-serif": ["Arial", "DejaVu Sans"],
    "font.family": "sans-serif",
    "figure.dpi": 300,
    "axes.edgecolor": "#CBD5E1",
    "axes.linewidth": 0.8,
    "text.color": "#0F172A",
})


def generate_architecture_diagram() -> None:
    # 6.6 x 3.1 дюйма (168 мм x 79 мм)
    fig, ax = plt.subplots(figsize=(6.6, 3.1), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 50)
    ax.axis("off")

    # Диспетчер
    ax.add_patch(
        patches.FancyBboxPatch(
            (2, 17), 18, 16, boxstyle="round,pad=0.5", facecolor="#F8FAFC", edgecolor="#64748B", linewidth=1.0
        )
    )
    ax.text(11, 27, "Диспетчер", ha="center", va="center", fontsize=7.5, weight="bold", color="#0F172A")
    ax.text(11, 21, "Модель: AR-210\nОшибка: E-17", ha="center", va="center", fontsize=6.5, color="#475569")

    # Стрелка Диспетчер -> Агент
    ax.annotate("", xy=(26, 25), xytext=(20, 25), arrowprops={"arrowstyle": "-|>", "lw": 1.2, "color": "#334155"})

    # Центральный ReAct Агент
    ax.add_patch(
        patches.FancyBboxPatch(
            (26, 8), 24, 34, boxstyle="round,pad=0.6", facecolor="#EEF2FF", edgecolor="#4F46E5", linewidth=1.4
        )
    )
    ax.text(38, 37.5, "ReAct-агент", ha="center", va="center", fontsize=8.5, weight="bold", color="#312E81")
    agent_body = (
        "• Thought-Action-Loop\n"
        "• Лимит max_steps=6\n"
        "• Проверка заземления\n"
        "• Фильтр галлюцинаций\n"
        "• Дедупликация шагов"
    )
    ax.text(38, 22.5, agent_body, ha="center", va="center", fontsize=6.5, color="#1E293B", linespacing=1.4)

    # 3 Контура справа (строго ортогональные связи)
    # Контур 1: Граф RAG
    ax.add_patch(
        patches.FancyBboxPatch(
            (58, 34), 39, 13, boxstyle="round,pad=0.5", facecolor="#F8FAFC", edgecolor="#475569", linewidth=1.0
        )
    )
    ax.text(77.5, 43, "Граф знаний (Graph RAG)", ha="center", va="center", fontsize=7.5, weight="bold", color="#0F172A")
    g_text = "• local_search: пути ≤ 3 хопов + замены REPLACED_BY\n• global_search: Map-Reduce по 24 сообществам"
    ax.text(77.5, 38, g_text, ha="center", va="center", fontsize=6, color="#475569")

    # Контур 2: ERP
    ax.add_patch(
        patches.FancyBboxPatch(
            (58, 18), 39, 13, boxstyle="round,pad=0.5", facecolor="#F8FAFC", edgecolor="#475569", linewidth=1.0
        )
    )
    ax.text(77.5, 27, "Учётная система (ERP)", ha="center", va="center", fontsize=7.5, weight="bold", color="#0F172A")
    erp_text = "• check_stock (5 складов) / get_price (цены)\n• 3 повтора при недоступности сети (ErpUnavailable)"
    ax.text(77.5, 22, erp_text, ha="center", va="center", fontsize=6, color="#475569")

    # Контур 3: Human-in-the-Loop Gateway
    ax.add_patch(
        patches.FancyBboxPatch(
            (58, 2), 39, 13, boxstyle="round,pad=0.5", facecolor="#FEF2F2", edgecolor="#DC2626", linewidth=1.2
        )
    )
    sec_title = "Шлюз безопасности (FR-9, FR-10)"
    ax.text(77.5, 11, sec_title, ha="center", va="center", fontsize=7.5, weight="bold", color="#991B1B")
    sec_text = "• confirm=False: перехват вызова create_service_order\n• Формирование pending_action для диспетчера"
    ax.text(77.5, 6, sec_text, ha="center", va="center", fontsize=6, color="#7F1D1D")

    # Ортогональные стрелки от Агента к контурам
    # К графу (вверх и вправо)
    ax.plot([50, 54, 54, 58], [25, 25, 40.5, 40.5], color="#475569", lw=1.1)
    ax.annotate("", xy=(58, 40.5), xytext=(56, 40.5), arrowprops={"arrowstyle": "-|>", "color": "#475569", "lw": 1.1})

    # К ERP (прямо по центру)
    ax.plot([50, 58], [24.5, 24.5], color="#475569", lw=1.1)
    ax.annotate("", xy=(58, 24.5), xytext=(56, 24.5), arrowprops={"arrowstyle": "-|>", "color": "#475569", "lw": 1.1})

    # К шлюзу безопасности (вниз и вправо)
    ax.plot([50, 54, 54, 58], [25, 25, 8.5, 8.5], color="#DC2626", lw=1.2)
    ax.annotate("", xy=(58, 8.5), xytext=(56, 8.5), arrowprops={"arrowstyle": "-|>", "color": "#DC2626", "lw": 1.2})

    plt.tight_layout()
    out_path = FIGURES_DIR / "architecture_diagram.png"
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()


def generate_subgraph_topology() -> None:
    # 6.6 x 3.1 дюйма (168 мм x 79 мм)
    fig, ax = plt.subplots(figsize=(6.6, 3.1), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 60)
    ax.axis("off")

    node_boxes = {
        "model": {
            "x": 2, "y": 42, "w": 18, "h": 12, "title": "Model:", "name": "AR-210",
            "bg": "#EFF6FF", "border": "#3B82F6", "tc": "#1E40AF",
        },
        "error": {
            "x": 2, "y": 18, "w": 18, "h": 12, "title": "ErrorCode:", "name": "E-17",
            "bg": "#FEF2F2", "border": "#EF4444", "tc": "#991B1B",
        },
        "proc": {
            "x": 2, "y": 2, "w": 18, "h": 10, "title": "Procedure:", "name": "SP-104",
            "bg": "#F0F9FF", "border": "#0EA5E9", "tc": "#0369A1",
        },
        "comp": {
            "x": 36, "y": 18, "w": 25, "h": 12, "title": "Component:", "name": "пусковое реле",
            "bg": "#FEF3C7", "border": "#D97706", "tc": "#92400E",
        },
        "part_old": {
            "x": 36, "y": 42, "w": 25, "h": 12, "title": "Part (снята):", "name": "P-1042",
            "bg": "#F1F5F9", "border": "#64748B", "tc": "#334155", "ls": "--",
        },
        "part_new": {
            "x": 72, "y": 42, "w": 26, "h": 12, "title": "Part (замена):", "name": "P-1042B",
            "bg": "#ECFDF5", "border": "#10B981", "tc": "#065F46", "lw": 1.5,
        },
        "supp": {
            "x": 72, "y": 18, "w": 26, "h": 12, "title": "Supplier:", "name": "ХолодКомплект",
            "bg": "#F5F3FF", "border": "#8B5CF6", "tc": "#5B21B6",
        },
    }

    for d in node_boxes.values():
        style = d.get("ls", "-")
        lw = d.get("lw", 1.1)
        ax.add_patch(
            patches.FancyBboxPatch(
                (d["x"], d["y"]), d["w"], d["h"],
                boxstyle="round,pad=0.4",
                facecolor=d["bg"],
                edgecolor=d["border"],
                linestyle=style,
                linewidth=lw,
            )
        )
        mid_x = d["x"] + d["w"] / 2
        mid_y = d["y"] + d["h"] / 2
        ax.text(mid_x, mid_y + 2.2, d["title"], ha="center", va="center", fontsize=6, color="#64748B", weight="bold")
        ax.text(mid_x, mid_y - 2.2, d["name"], ha="center", va="center", fontsize=7.5, color=d["tc"], weight="bold")

    def draw_edge(
        x1: float, y1: float, x2: float, y2: float, label: str,
        color: str = "#475569", bold: bool = False, lw: float = 1.1
    ) -> None:
        ax.annotate(
            "", xy=(x2, y2), xytext=(x1, y1),
            arrowprops={"arrowstyle": "-|>", "color": color, "lw": lw, "shrinkA": 4, "shrinkB": 4}
        )
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        weight = "bold" if bold else "normal"
        box_props = {
            "boxstyle": "round,pad=0.2", "facecolor": "#FFFFFF",
            "edgecolor": color, "linewidth": 0.5, "alpha": 0.95,
        }
        ax.text(
            mx, my, label, ha="center", va="center", fontsize=5.8,
            color=color, weight=weight, bbox=box_props
        )

    draw_edge(20, 48, 36, 48, "HAS_PART")
    draw_edge(48.5, 42, 48.5, 30, "IS_A")
    draw_edge(20, 24, 36, 24, "INDICATES")
    draw_edge(11, 18, 11, 12, "FIXED_BY")
    draw_edge(61, 48, 72, 48, "REPLACED_BY", color="#DC2626", bold=True, lw=1.4)
    draw_edge(85, 42, 85, 30, "SUPPLIED_BY")

    ax.add_patch(
        patches.FancyBboxPatch(
            (36, 2), 62, 10, boxstyle="round,pad=0.4", facecolor="#F8FAFC", edgecolor="#CBD5E1", linewidth=0.8
        )
    )
    callout = (
        "Цепочка актуальной замены: P-1042 -> REPLACED_BY -> P-1042B -> SUPPLIED_BY -> ХолодКомплект\n"
        "Обрыв на multihop: путь AR-210 -> P-1042 -> P-1042B -> ХолодКомплект (4 ребра) превышает max_hops ≤ 3"
    )
    ax.text(67, 7, callout, ha="center", va="center", fontsize=6, color="#475569", style="italic")

    plt.tight_layout()
    out_path = FIGURES_DIR / "subgraph_topology.png"
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()


def generate_benchmark_comparison() -> None:
    # 6.6 x 2.8 дюйма (168 мм x 71 мм)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6.6, 2.8), dpi=300, gridspec_kw={"width_ratios": [1.45, 1]})

    categories = ["Local (5)", "Multihop (7)", "Global (4)", "Tool (5)", "Refusal (3)", "Все (24)"]
    x = range(len(categories))
    width = 0.2

    baseline_vals = [1.000, 0.571, 0.000, 0.000, 1.000, 0.500]
    local_vals = [0.800, 0.143, 0.500, 0.000, 1.000, 0.417]
    global_vals = [0.600, 0.286, 0.000, 0.000, 0.000, 0.208]
    agent_vals = [0.800, 0.143, 0.000, 0.200, 0.000, 0.250]

    ax1.bar([i - 1.5 * width for i in x], baseline_vals, width, label="Flat RAG", color="#64748B")
    ax1.bar([i - 0.5 * width for i in x], local_vals, width, label="Local Graph", color="#0D9488")
    ax1.bar([i + 0.5 * width for i in x], global_vals, width, label="Global Graph", color="#8B5CF6")
    ax1.bar([i + 1.5 * width for i in x], agent_vals, width, label="Agent", color="#2563EB")

    ax1.set_ylabel("Доля верных ответов (Accuracy)", fontsize=7, color="#475569")
    ax1.set_title("Точность по типам вопросов", fontsize=8, weight="bold", color="#1E293B", pad=8)
    ax1.set_xticks(list(x))
    ax1.set_xticklabels(categories, fontsize=6.5)
    ax1.set_ylim(0, 1.15)
    ax1.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.5, color="#CBD5E1")
    ax1.legend(loc="upper right", fontsize=6, frameon=True, facecolor="#FFFFFF", edgecolor="#E2E8F0")

    for spine in ["top", "right"]:
        ax1.spines[spine].set_visible(False)
        ax2.spines[spine].set_visible(False)

    modes = ["Local", "Flat RAG", "Agent", "Global"]
    tokens = [238.7, 1356.2, 5461.5, 16471.7]
    bar_colors = ["#0D9488", "#64748B", "#2563EB", "#8B5CF6"]

    bars = ax2.bar(modes, tokens, color=bar_colors, width=0.55)
    ax2.set_ylabel("Токенов на вопрос", fontsize=7, color="#475569")
    ax2.set_title("Стоимость режимов (Токены)", fontsize=8, weight="bold", color="#1E293B", pad=8)
    ax2.set_xticks(range(len(modes)))
    ax2.set_xticklabels(modes, fontsize=6.5)
    ax2.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.5, color="#CBD5E1")

    for bar, val in zip(bars, tokens, strict=True):
        yval = bar.get_height()
        ax2.text(
            bar.get_x() + bar.get_width() / 2, yval + 350,
            f"{val:.0f}", ha="center", va="bottom", fontsize=6.5, weight="bold", color="#334155"
        )

    ax2.annotate(
        "в 5.7 раз дешевле Flat RAG",
        xy=(0, 300),
        xytext=(0.4, 5200),
        arrowprops={"arrowstyle": "->", "lw": 0.8, "color": "#0D9488", "connectionstyle": "arc3,rad=-0.2"},
        fontsize=6,
        color="#0D9488",
        weight="bold",
    )

    plt.tight_layout()
    out_path = FIGURES_DIR / "benchmark_comparison.png"
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()


def generate_safety_flowchart() -> None:
    # 6.6 x 2.7 дюйма (168 мм x 68 мм)
    fig, ax = plt.subplots(figsize=(6.6, 2.7), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 48)
    ax.axis("off")

    # Блок 1: Вход
    ax.add_patch(
        patches.FancyBboxPatch(
            (2, 19), 16, 12, boxstyle="round,pad=0.4",
            facecolor="#F8FAFC", edgecolor="#64748B", linewidth=1.0
        )
    )
    ax.text(10, 26, "Действие модели", ha="center", va="center", fontsize=7, weight="bold", color="#0F172A")
    ax.text(10, 22, "(Tool Call)", ha="center", va="center", fontsize=6, color="#64748B")

    ax.annotate("", xy=(24, 25), xytext=(18, 25), arrowprops={"arrowstyle": "-|>", "lw": 1.0, "color": "#475569"})

    # Блок 2: Валидация аргументов
    ax.add_patch(
        patches.FancyBboxPatch(
            (24, 19), 20, 12, boxstyle="round,pad=0.4",
            facecolor="#F8FAFC", edgecolor="#64748B", linewidth=1.0
        )
    )
    ax.text(34, 26.5, "1. Параметры", ha="center", va="center", fontsize=6.5, weight="bold", color="#0F172A")
    ax.text(34, 22, "• Склад (5 городов)\n• Формат Part ID", ha="center", va="center", fontsize=5.8, color="#475569")

    ax.annotate("", xy=(50, 25), xytext=(44, 25), arrowprops={"arrowstyle": "-|>", "lw": 1.0, "color": "#475569"})

    # Блок 3: Заземление Part
    ax.add_patch(
        patches.FancyBboxPatch(
            (50, 19), 20, 12, boxstyle="round,pad=0.4",
            facecolor="#F8FAFC", edgecolor="#64748B", linewidth=1.0
        )
    )
    ax.text(60, 26.5, "2. Заземление Part ID", ha="center", va="center", fontsize=6.5, weight="bold", color="#0F172A")
    ax.text(60, 22, "Деталь в вопросе или\nнайдена в графе?", ha="center", va="center", fontsize=5.8, color="#475569")

    # Ветка отклонения вниз (FR-7)
    ax.annotate("", xy=(34, 10), xytext=(34, 19), arrowprops={"arrowstyle": "-|>", "lw": 1.0, "color": "#DC2626"})
    ax.annotate("", xy=(60, 10), xytext=(60, 19), arrowprops={"arrowstyle": "-|>", "lw": 1.0, "color": "#DC2626"})
    ax.add_patch(
        patches.FancyBboxPatch(
            (24, 2), 46, 8, boxstyle="round,pad=0.4",
            facecolor="#FEF2F2", edgecolor="#DC2626", linewidth=1.0
        )
    )
    rej_txt = "ОТКЛОНЕНИЕ: возврат ошибки модели (FR-7)"
    ax.text(47, 6, rej_txt, ha="center", va="center", fontsize=6.5, color="#991B1B", weight="bold")

    ax.annotate("", xy=(76, 25), xytext=(70, 25), arrowprops={"arrowstyle": "-|>", "lw": 1.0, "color": "#475569"})

    # Блок 4: Мутация или чтение?
    ax.add_patch(
        patches.FancyBboxPatch(
            (76, 19), 22, 12, boxstyle="round,pad=0.4",
            facecolor="#EEF2FF", edgecolor="#4F46E5", linewidth=1.2
        )
    )
    ax.text(87, 26.5, "3. Тип операции", ha="center", va="center", fontsize=6.5, weight="bold", color="#312E81")
    ax.text(87, 22, "Мутирующий заказ\nили чтение данных?", ha="center", va="center", fontsize=5.8, color="#4338CA")

    # Ветка чтения наверх
    ax.plot([87, 87], [31, 38], color="#0D9488", lw=1.0)
    ax.annotate("", xy=(87, 38), xytext=(87, 34), arrowprops={"arrowstyle": "-|>", "lw": 1.0, "color": "#0D9488"})
    ax.add_patch(
        patches.FancyBboxPatch(
            (76, 38), 22, 8, boxstyle="round,pad=0.4",
            facecolor="#F0FDF4", edgecolor="#0D9488", linewidth=1.0
        )
    )
    read_txt = "Чтение: ERP API\n(/stock, /parts)"
    ax.text(87, 42, read_txt, ha="center", va="center", fontsize=6, color="#065F46", weight="bold")

    # Ветка заказа вниз (Human-in-the-Loop)
    ax.plot([87, 87], [19, 12], color="#DC2626", lw=1.2)
    ax.annotate("", xy=(87, 12), xytext=(87, 16), arrowprops={"arrowstyle": "-|>", "lw": 1.2, "color": "#DC2626"})
    ax.add_patch(
        patches.FancyBboxPatch(
            (74, 2), 24, 10, boxstyle="round,pad=0.4",
            facecolor="#FEF2F2", edgecolor="#DC2626", linewidth=1.2
        )
    )
    order_txt = "confirm=False: STOP\npending_action (FR-9)"
    ax.text(86, 7, order_txt, ha="center", va="center", fontsize=6.5, color="#991B1B", weight="bold")

    plt.tight_layout()
    out_path = FIGURES_DIR / "safety_flowchart.png"
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()


def main() -> None:
    generate_architecture_diagram()
    generate_subgraph_topology()
    generate_benchmark_comparison()
    generate_safety_flowchart()
    print("Все 4 иллюстрации успешно сгенерированы в папку figures/")


if __name__ == "__main__":
    main()
