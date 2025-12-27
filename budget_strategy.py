# budget_strategy.py

class BudgetStrategy:
    def check(self, spent, budget):
        raise NotImplementedError
class WarningBudgetStrategy(BudgetStrategy):
    def check(self, spent, budget):
        ratio = spent / budget
        if ratio >= 1:
            return "超支"
        elif ratio >= 0.8:
            return "接近超支"
        else:
            return "正常"
class BudgetChecker:
    def __init__(self, strategy: BudgetStrategy):
        self.strategy = strategy

    def run(self, spent, budget):
        return self.strategy.check(spent, budget)
