"""Скрипт генерации графических материалов для отчёта REPORT.pdf."""

from pathlib import Path

import matplotlib.patches as patches
import matplotlib.pyplot as plt
import networkx as nx

FIGURES_DIR = Path("figures")
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial"]
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["figure.dpi"] = 300


def generate_architecture_diagram() -> None:
    fig, ax = plt.subplots(figsize=(9, 4.5), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 60)
    ax.axis("off")

    # Диспетчер
    ax.add_patch(
        patches.FancyBboxPatch(
            (2, 22), 16, 16, boxstyle="round,pad=1.5", facecolor="#f1f5f9", edgecolor="#334155", linewidth=1.5
        )
    )
    disp_text = "Диспетчер\nсервисной службы\n(Модель + Ошибка)"
    ax.text(10, 31, disp_text, ha="center", va="center", fontsize=8, weight="bold", color="#0f172a")

    # Стрелка к Агенту
    ax.annotate("", xy=(24, 30), xytext=(19, 30), arrowprops={"arrowstyle": "->", "lw": 2, "color": "#1e3a8a"})

    # Центральный ReAct Агент
    ax.add_patch(
        patches.FancyBboxPatch(
            (24, 12), 24, 36, boxstyle="round,pad=1.5", facecolor="#eff6ff", edgecolor="#1e3a8a", linewidth=2
        )
    )
    ax.text(36, 42, "ReAct-агент\n«ПолярТех»", ha="center", va="center", fontsize=9.5, weight="bold", color="#1e3a8a")
    react_features = (
        "• Thought-Action-Observation\n"
        "• Лимит max_steps=6\n"
        "• Проверка заземления\n"
        "• Фильтр галлюцинаций\n"
        "• Дедупликация шагов"
    )
    ax.text(36, 25, react_features, ha="center", va="center", fontsize=7.5, color="#1e293b")

    # Контур 1: Граф знаний
    ax.add_patch(
        patches.FancyBboxPatch(
            (56, 40), 40, 17, boxstyle="round,pad=1.2", facecolor="#f0fdf4", edgecolor="#16a34a", linewidth=1.5
        )
    )
    ax.text(76, 52, "Граф знаний (Graph RAG)", ha="center", va="center", fontsize=8.5, weight="bold", color="#16a34a")
    graph_sub = (
        "• local_search: пути ≤ 3 хопов + замены REPLACED_BY\n"
        "• global_search: Map-Reduce по 24 сообществам"
    )
    ax.text(76, 45, graph_sub, ha="center", va="center", fontsize=7, color="#14532d")

    # Контур 2: ERP
    ax.add_patch(
        patches.FancyBboxPatch(
            (56, 21), 40, 16, boxstyle="round,pad=1.2", facecolor="#fefce8", edgecolor="#ca8a04", linewidth=1.5
        )
    )
    ax.text(76, 32, "Учётная система (ERP)", ha="center", va="center", fontsize=8.5, weight="bold", color="#ca8a04")
    erp_sub = (
        "• check_stock: остатки по складам (5 городов)\n"
        "• get_price: актуальные цены и статус детали\n"
        "• 3 повтора при сбоях сети (ErpUnavailable)"
    )
    ax.text(76, 25, erp_sub, ha="center", va="center", fontsize=7, color="#713f12")

    # Контур 3: Human in the loop
    ax.add_patch(
        patches.FancyBboxPatch(
            (56, 3), 40, 15, boxstyle="round,pad=1.2", facecolor="#fef2f2", edgecolor="#dc2626", linewidth=1.5
        )
    )
    sec_title = "Шлюз безопасности (FR-9, FR-10)"
    ax.text(76, 13, sec_title, ha="center", va="center", fontsize=8.5, weight="bold", color="#dc2626")
    sec_sub = (
        "• create_service_order: перехват при confirm=False\n"
        "• Выдача pending_action для согласования человеком"
    )
    ax.text(76, 7, sec_sub, ha="center", va="center", fontsize=7, color="#7f1d1d")

    # Стрелки от агента
    ax.annotate("", xy=(55, 48), xytext=(49, 36), arrowprops={"arrowstyle": "<->", "lw": 1.5, "color": "#16a34a"})
    ax.annotate("", xy=(55, 29), xytext=(49, 30), arrowprops={"arrowstyle": "<->", "lw": 1.5, "color": "#ca8a04"})
    ax.annotate("", xy=(55, 11), xytext=(49, 24), arrowprops={"arrowstyle": "->", "lw": 1.5, "color": "#dc2626"})

    plt.tight_layout()
    out_path = FIGURES_DIR / "architecture_diagram.png"
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()


def generate_subgraph_topology() -> None:
    fig, ax = plt.subplots(figsize=(8.5, 4.5), dpi=300)
    g = nx.DiGraph()

    nodes = {
        "Model:AR-210": {"type": "Model", "color": "#1e3a8a", "label": "Model:\nAR-210"},
        "ErrorCode:E-17": {"type": "ErrorCode", "color": "#dc2626", "label": "ErrorCode:\nE-17"},
        "Component:пусковое реле": {"type": "Component", "color": "#d97706", "label": "Component:\nпусковое реле"},
        "Part:P-1042": {"type": "Part", "color": "#94a3b8", "label": "Part:\nP-1042 (снята)"},
        "Part:P-1042B": {"type": "Part", "color": "#059669", "label": "Part:\nP-1042B (замена)"},
        "Supplier:ХолодКомплект": {"type": "Supplier", "color": "#7c3aed", "label": "Supplier:\nХолодКомплект"},
        "Procedure:SP-104": {"type": "Procedure", "color": "#0284c7", "label": "Procedure:\nSP-104"},
    }

    for n, attrs in nodes.items():
        g.add_node(n, **attrs)

    edges = [
        ("Model:AR-210", "Part:P-1042", "HAS_PART"),
        ("ErrorCode:E-17", "Component:пусковое реле", "INDICATES"),
        ("ErrorCode:E-17", "Procedure:SP-104", "FIXED_BY"),
        ("Part:P-1042", "Component:пусковое реле", "IS_A"),
        ("Part:P-1042", "Part:P-1042B", "REPLACED_BY"),
        ("Part:P-1042B", "Supplier:ХолодКомплект", "SUPPLIED_BY"),
    ]

    for u, v, lbl in edges:
        g.add_edge(u, v, label=lbl)

    pos = {
        "Model:AR-210": (0.1, 0.8),
        "Part:P-1042": (0.4, 0.8),
        "Part:P-1042B": (0.7, 0.8),
        "Supplier:ХолодКомплект": (0.95, 0.8),
        "Component:пусковое реле": (0.4, 0.25),
        "ErrorCode:E-17": (0.1, 0.25),
        "Procedure:SP-104": (0.1, -0.2),
    }

    for n, p in pos.items():
        color = nodes[n]["color"]
        ax.scatter(p[0], p[1], s=2600, color=color, zorder=3, edgecolors="#0f172a", linewidth=1.5)
        ax.text(
            p[0], p[1], nodes[n]["label"],
            ha="center", va="center", color="white", fontsize=7, weight="bold", zorder=4
        )

    for u, v, label in edges:
        p1 = pos[u]
        p2 = pos[v]
        edge_color = "#dc2626" if label == "REPLACED_BY" else "#475569"
        lw = 2.0 if label == "REPLACED_BY" else 1.2
        ax.annotate(
            "",
            xy=p2,
            xytext=p1,
            arrowprops={
                "arrowstyle": "-|>",
                "color": edge_color,
                "lw": lw,
                "shrinkA": 22,
                "shrinkB": 22,
                "mutation_scale": 12,
            },
            zorder=2,
        )
        mid_x = (p1[0] + p2[0]) / 2
        mid_y = (p1[1] + p2[1]) / 2 + 0.05
        ax.text(
            mid_x,
            mid_y,
            label,
            ha="center",
            va="center",
            fontsize=6.5,
            weight="bold",
            color=edge_color,
            bbox={"boxstyle": "round,pad=0.2", "facecolor": "white", "edgecolor": edge_color, "alpha": 0.9},
            zorder=5,
        )

    callout_txt = (
        "Траектория замены детали:\n"
        "P-1042 (снята с производства) -> REPLACED_BY -> P-1042B -> SUPPLIED_BY -> ХолодКомплект\n"
        "(Локальный поиск находит замену, но 4-шаговый путь обрывается при ограничении max_hops ≤ 3)"
    )
    ax.text(
        0.55,
        -0.15,
        callout_txt,
        ha="center",
        va="center",
        fontsize=7,
        style="italic",
        bbox={"boxstyle": "round,pad=0.5", "facecolor": "#f8fafc", "edgecolor": "#cbd5e1"},
    )

    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.3, 0.95)
    ax.axis("off")
    plt.tight_layout()
    out_path = FIGURES_DIR / "subgraph_topology.png"
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()


def generate_benchmark_comparison() -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.5, 4.2), dpi=300, gridspec_kw={"width_ratios": [1.4, 1]})

    categories = ["Local (5)", "Multihop (7)", "Global (4)", "Tool (5)", "Refusal (3)", "Все (24)"]
    x = range(len(categories))
    width = 0.2

    baseline_vals = [1.000, 0.571, 0.000, 0.000, 1.000, 0.500]
    local_vals = [0.800, 0.143, 0.500, 0.000, 1.000, 0.417]
    global_vals = [0.600, 0.286, 0.000, 0.000, 0.000, 0.208]
    agent_vals = [0.800, 0.143, 0.000, 0.200, 0.000, 0.250]

    ax1.bar([i - 1.5 * width for i in x], baseline_vals, width, label="Baseline (Flat)", color="#3b82f6")
    ax1.bar([i - 0.5 * width for i in x], local_vals, width, label="Local (Graph)", color="#10b981")
    ax1.bar([i + 0.5 * width for i in x], global_vals, width, label="Global (Graph)", color="#8b5cf6")
    ax1.bar([i + 1.5 * width for i in x], agent_vals, width, label="Agent (Граф+ERP)", color="#f59e0b")

    ax1.set_ylabel("Доля верных ответов (Accuracy)", fontsize=8, weight="bold")
    ax1.set_title("Точность по типам вопросов", fontsize=9.5, weight="bold", color="#1e3a8a")
    ax1.set_xticks(list(x))
    ax1.set_xticklabels(categories, fontsize=7.5)
    ax1.set_ylim(0, 1.15)
    ax1.grid(axis="y", linestyle="--", alpha=0.4)
    ax1.legend(loc="upper right", fontsize=7)

    modes = ["Local (Graph)", "Baseline (Flat)", "Agent (Граф+ERP)", "Global (Graph)"]
    tokens = [238.7, 1356.2, 5461.5, 16471.7]
    bar_colors = ["#10b981", "#3b82f6", "#f59e0b", "#8b5cf6"]

    bars = ax2.bar(modes, tokens, color=bar_colors, width=0.55)
    ax2.set_ylabel("Токенов на один вопрос", fontsize=8, weight="bold")
    ax2.set_title("Стоимость режимов (Токены на вопрос)", fontsize=9.5, weight="bold", color="#1e3a8a")
    ax2.set_xticks(range(len(modes)))
    ax2.set_xticklabels(modes, fontsize=7, rotation=15)
    ax2.grid(axis="y", linestyle="--", alpha=0.4)

    for bar, val in zip(bars, tokens, strict=True):
        yval = bar.get_height()
        ax2.text(
            bar.get_x() + bar.get_width() / 2, yval + 300,
            f"{val:.0f}", ha="center", va="bottom", fontsize=7.5, weight="bold"
        )

    ax2.annotate(
        "В 5.7 раз дешевле\nFlat RAG!",
        xy=(0, 240),
        xytext=(0.5, 5500),
        arrowprops={"arrowstyle": "->", "lw": 1.2, "color": "#059669"},
        fontsize=7,
        weight="bold",
        color="#059669",
        bbox={"boxstyle": "round,pad=0.3", "facecolor": "#ecfdf5", "edgecolor": "#10b981"},
    )

    plt.tight_layout()
    out_path = FIGURES_DIR / "benchmark_comparison.png"
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()


def generate_safety_flowchart() -> None:
    fig, ax = plt.subplots(figsize=(8.5, 4.2), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 50)
    ax.axis("off")

    # Step 1: Input
    ax.add_patch(
        patches.FancyBboxPatch((4, 20), 16, 12, boxstyle="round,pad=1", facecolor="#e2e8f0", edgecolor="#475569")
    )
    ax.text(12, 26, "Действие модели\n(Tool Call)", ha="center", va="center", fontsize=7.5, weight="bold")

    ax.annotate("", xy=(26, 26), xytext=(20, 26), arrowprops={"arrowstyle": "->", "lw": 1.5, "color": "#1e3a8a"})

    # Step 2: Param Validation
    ax.add_patch(
        patches.FancyBboxPatch((26, 20), 18, 12, boxstyle="round,pad=1", facecolor="#fef9c3", edgecolor="#ca8a04")
    )
    ax.text(35, 26, "1. Проверка склада\n(Enum из 5 городов)\nи regex Part ID", ha="center", va="center", fontsize=7)

    ax.annotate("", xy=(50, 26), xytext=(44, 26), arrowprops={"arrowstyle": "->", "lw": 1.5, "color": "#1e3a8a"})

    # Step 3: Grounding
    ax.add_patch(
        patches.FancyBboxPatch((50, 20), 18, 12, boxstyle="round,pad=1", facecolor="#fef9c3", edgecolor="#ca8a04")
    )
    ax.text(59, 26, "2. Заземление Part:\nдеталь из вопроса\nили из базы знаний?", ha="center", va="center", fontsize=7)

    # Reject branch
    ax.annotate("", xy=(35, 8), xytext=(35, 20), arrowprops={"arrowstyle": "->", "lw": 1.2, "color": "#dc2626"})
    ax.annotate("", xy=(59, 8), xytext=(59, 20), arrowprops={"arrowstyle": "->", "lw": 1.2, "color": "#dc2626"})
    ax.add_patch(
        patches.FancyBboxPatch((28, 2), 38, 7, boxstyle="round,pad=0.8", facecolor="#fef2f2", edgecolor="#dc2626")
    )
    ax.text(
        47, 5.5, "ОТКЛОНЕНИЕ: возврат ошибки модели (FR-7)",
        ha="center", va="center", fontsize=7, color="#dc2626", weight="bold"
    )

    ax.annotate("", xy=(74, 26), xytext=(68, 26), arrowprops={"arrowstyle": "->", "lw": 1.5, "color": "#1e3a8a"})

    # Step 4: Mutating operation check
    ax.add_patch(
        patches.FancyBboxPatch((74, 20), 22, 12, boxstyle="round,pad=1", facecolor="#dbeafe", edgecolor="#1d4ed8")
    )
    ax.text(
        85, 26, "3. Мутирующая\nоперация заказа?\n(create_order)",
        ha="center", va="center", fontsize=7, weight="bold"
    )

    # Read branch
    ax.annotate(
        "Нет (чтение)", xy=(85, 42), xytext=(85, 32),
        arrowprops={"arrowstyle": "->", "lw": 1.2, "color": "#16a34a"},
        fontsize=7, color="#16a34a", weight="bold"
    )
    ax.add_patch(
        patches.FancyBboxPatch((74, 41), 22, 7, boxstyle="round,pad=0.8", facecolor="#f0fdf4", edgecolor="#16a34a")
    )
    ax.text(
        85, 44.5, "Прямой запрос к ERP API\n(/stock, /parts)",
        ha="center", va="center", fontsize=7, color="#16a34a"
    )

    # Confirm branch
    ax.annotate(
        "Да (заказ)", xy=(85, 12), xytext=(85, 20),
        arrowprops={"arrowstyle": "->", "lw": 1.2, "color": "#dc2626"},
        fontsize=7, color="#dc2626", weight="bold"
    )
    ax.add_patch(
        patches.FancyBboxPatch(
            (71, 2), 27, 9, boxstyle="round,pad=0.8", facecolor="#fee2e2", edgecolor="#b91c1c", linewidth=1.5
        )
    )
    ax.text(
        84.5, 6.5, "Human-in-the-Loop:\nconfirm=False -> STOP\nВыдача pending_action (FR-9)",
        ha="center", va="center", fontsize=7, color="#991b1b", weight="bold"
    )

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
