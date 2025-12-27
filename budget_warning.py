# -*- coding: utf-8 -*-
from typing import Dict, List, Tuple

def check_budget(expenses_by_cat: Dict[str, float],
                 budgets_by_cat: Dict[str, float],
                 near_threshold: float = 0.8) -> Tuple[List[str], List[str]]:
    near, over = [], []
    for cat, spent in expenses_by_cat.items():
        if not cat:
            continue
        budget = budgets_by_cat.get(cat, 0)
        if budget <= 0:
            continue
        ratio = spent / budget
        if ratio >= 1:
            over.append(f"⛔ {cat} 超支：{spent:,.0f} / {budget:,.0f}（{ratio*100:.0f}%）")
        elif ratio >= near_threshold:
            near.append(f"⚠ {cat} 接近超支：{spent:,.0f} / {budget:,.0f}（{ratio*100:.0f}%）")
    return near, over
