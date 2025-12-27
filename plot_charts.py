# -*- coding: utf-8 -*-
from typing import Dict, List, Optional
import matplotlib.ticker as mticker
import matplotlib.patches as mpatches


def plot_monthly(
    expense_by_cat: Dict[str, float],
    cum_x: List[int],      # 日期（天）- 目前支出用得到
    cum_y: List[float],    # 累計支出
    canvas,
    month_title: str,
    note: Optional[str] = None,
    month_income: float = 0.0,   # ✅ 新增：從 main_gui 傳進來
):
    fig = canvas.figure
    fig.clear()
    fig.set_constrained_layout(True)

    # =====================
    # 左：甜甜圈（支出分類比例）——保持你現在的板
    # =====================
    cats = [k for k, v in expense_by_cat.items() if k and v > 0]
    vals = [float(expense_by_cat[k]) for k in cats]

    ax1 = fig.add_subplot(121)

    if not vals:
        ax1.text(0.5, 0.5, "本月尚無支出", ha="center", va="center", fontsize=13)
        ax1.axis("off")
    else:
        ax1.pie(
            vals,
            labels=cats,
            autopct="%1.0f%%",
            startangle=90,
            pctdistance=0.8
        )
        ax1.add_artist(mpatches.Circle((0, 0), 0.55, fc="white"))
        ax1.axis("equal")

        total_expense = sum(vals)
        ax1.text(
            0, 0,
            f"總支出\n{total_expense:,.0f}",
            ha="center", va="center",
            fontsize=12, fontweight="bold"
        )
        ax1.set_title(f"{month_title} 支出比例")

    for s in ax1.spines.values():
        s.set_visible(False)

    # =====================
    # 右：收入 / 支出 / 結餘（三根柱狀）——✅ 加收入進去、而且不會有框框
    # =====================
    ax2 = fig.add_subplot(122)
    ax2.set_title(f"{month_title} 收入 / 支出 / 結餘")
    ax2.set_ylabel("金額")
    ax2.yaxis.set_major_formatter(mticker.StrMethodFormatter("{x:,.0f}"))
    ax2.grid(True, axis="y", alpha=0.25)

    month_expense = float(cum_y[-1]) if cum_y else 0.0
    income = float(month_income)
    expense = month_expense
    balance = income - expense

    labels = ["收入", "支出", "結餘"]
    values = [income, expense, balance]

    # 無邊框（避免任何「框感」）
    ax2.bar(labels, values, alpha=0.8, edgecolor="none", linewidth=0)

    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)

    canvas.draw()
