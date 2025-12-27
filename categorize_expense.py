# -*- coding: utf-8 -*-
import sys
from datetime import date
from collections import defaultdict
from dataclasses import dataclass

from PyQt5.QtWidgets import *
from PyQt5.QtCore import QDate, Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from budget_warning import check_budget
from plot_charts import plot_monthly


@dataclass
class Record:
    d: date
    kind: str      # "收入" / "支出"
    note: str      # 自訂備註（可空）
    category: str  # 支出類別必填；收入固定 "收入"
    amount: float


def ym(d: date):
    return f"{d.year}-{d.month:02d}"


APP_QSS = """
QWidget { font-family: "Microsoft JhengHei"; font-size: 14px; }
#Title { font-size: 22px; font-weight: 800; padding: 10px; }
QTabWidget::pane { border: 1px solid #ddd; border-radius: 12px; padding: 6px; }
QTabBar::tab { padding: 10px 14px; margin-right: 6px; border-radius: 10px; background: #f3f4f6; }
QTabBar::tab:selected { background: #111827; color: white; }
QGroupBox { border: 1px solid #e5e7eb; border-radius: 14px; margin-top: 10px; padding: 10px; }
QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 0 6px; color: #111827; font-weight: 700; }
QLineEdit, QComboBox, QDateEdit, QDoubleSpinBox {
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    padding: 8px 10px;
    background: white;
}
QPushButton {
    border: none;
    border-radius: 10px;
    padding: 10px 12px;
    background: #111827;
    color: white;
    font-weight: 700;
}
QPushButton:hover { background: #1f2937; }
QPushButton:pressed { background: #0b1220; }
QTableWidget {
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    gridline-color: #e5e7eb;
    background: white;
}
QHeaderView::section {
    background: #f3f4f6;
    border: none;
    padding: 8px;
    font-weight: 700;
    color: #111827;
}
#Card {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 14px;
    padding: 12px;
}
#Hint { color: #6b7280; }
#OK { color: #059669; font-weight: 800; }
"""


class App(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("完整支出預警系統（支出手選類別）")
        self.resize(1100, 720)
        self.setStyleSheet(APP_QSS)

        self.records: list[Record] = []

        # ✅ 簡單類別（你說的「就簡單的飲食」這種）
        self.expense_categories = ["飲食", "交通", "娛樂", "生活", "教育", "醫療"]

        # 預算
        self.budgets = {
            "飲食": 3000,
            "交通": 1500,
            "娛樂": 2000,
            "生活": 1500,
            "教育": 2000,
            "醫療": 1000,
        }

        root = QVBoxLayout(self)
        title = QLabel("完整支出預警系統")
        title.setObjectName("Title")
        title.setAlignment(Qt.AlignCenter)
        root.addWidget(title)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs)

        self._build_tab_add()
        self._build_tab_report()

        self._refresh_months()
        self._refresh_table()
        self._refresh_add_chart()
        self._refresh_report()

    # ---------------- Tab: 記帳 ----------------
    def _build_tab_add(self):
        w = QWidget()
        layout = QHBoxLayout(w)

        left = QGroupBox("新增一筆收支")
        form = QFormLayout(left)

        self.kind = QComboBox()
        self.kind.addItems(["支出", "收入"])
        self.kind.currentTextChanged.connect(self._on_kind_change)

        self.date = QDateEdit(QDate.currentDate())
        self.date.setCalendarPopup(True)

        self.note = QLineEdit()
        self.note.setPlaceholderText("備註（可空白，例如：晚餐、加油、打工）")

        self.category = QComboBox()
        self.category.addItems(self.expense_categories)

        self.money = QDoubleSpinBox()
        self.money.setMaximum(999999999)
        self.money.setDecimals(0)
        self.money.setPrefix("$ ")
        self.money.setSingleStep(50)

        btn_add = QPushButton("新增")
        btn_add.clicked.connect(self.add_record)

        hint = QLabel("必填：日期 / 金額(>0)\n支出：必選類別（飲食/交通/…）｜收入：不用選類別")
        hint.setObjectName("Hint")

        self.status = QLabel("狀態：尚未新增資料")
        self.status.setObjectName("Hint")

        form.addRow("類型", self.kind)
        form.addRow("日期", self.date)
        form.addRow("備註", self.note)
        form.addRow("支出類別", self.category)
        form.addRow("金額", self.money)
        form.addRow(btn_add)
        form.addRow(hint)
        form.addRow(self.status)

        right = QGroupBox("明細（新增後會出現在這裡）")
        right_layout = QVBoxLayout(right)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["日期", "類型", "備註", "類別", "金額"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        right_layout.addWidget(self.table)

        self.fig_add = Figure(figsize=(6, 3.2))
        self.canvas_add = FigureCanvas(self.fig_add)
        right_layout.addWidget(self.canvas_add)

        layout.addWidget(left, 1)
        layout.addWidget(right, 2)
        self.tabs.addTab(w, "記帳")

        self._on_kind_change(self.kind.currentText())

    def _on_kind_change(self, kind: str):
        # ✅ 收入不需要選類別
        self.category.setEnabled(kind == "支出")

    def add_record(self):
        missing = []
        if self.money.value() <= 0:
            missing.append("金額（需大於 0）")
        if not self.date.date().isValid():
            missing.append("日期")

        kind = self.kind.currentText()
        if kind == "支出":
            cat = self.category.currentText().strip()
            if not cat:
                missing.append("支出類別（必選）")
        else:
            cat = "收入"

        if missing:
            QMessageBox.warning(self, "缺漏", "以下欄位沒填或不正確：\n- " + "\n- ".join(missing))
            return

        d = self.date.date().toPyDate()
        note = (self.note.text() or "").strip()

        self.records.append(Record(d=d, kind=kind, note=note, category=cat, amount=float(self.money.value())))

        self.note.clear()
        self.money.setValue(0)

        self._refresh_table()
        self._refresh_months(select=ym(d))
        self._refresh_add_chart()
        self._refresh_report()
        self._show_budget_alert_for_month(ym(d))

        self.status.setText("狀態：新增成功 ✅")
        self.status.setObjectName("OK")
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)

    def _refresh_table(self):
        self.table.setRowCount(0)
        for r in sorted(self.records, key=lambda x: x.d, reverse=True):
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(r.d.strftime("%Y-%m-%d")))
            self.table.setItem(row, 1, QTableWidgetItem(r.kind))
            self.table.setItem(row, 2, QTableWidgetItem(r.note))
            self.table.setItem(row, 3, QTableWidgetItem(r.category))
            self.table.setItem(row, 4, QTableWidgetItem(f"$ {r.amount:,.0f}"))

    # ---------------- Tab: 月報 ----------------
    def _build_tab_report(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        top = QHBoxLayout()
        top.addWidget(QLabel("選擇月份："))
        self.month = QComboBox()
        self.month.currentTextChanged.connect(lambda _: self._refresh_report())
        top.addWidget(self.month)
        top.addStretch(1)
        layout.addLayout(top)

        self.summary = QLabel("尚無資料")
        self.summary.setObjectName("Card")
        self.summary.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)

        self.fig_report = Figure(figsize=(8, 3.8))
        self.canvas_report = FigureCanvas(self.fig_report)
        layout.addWidget(self.canvas_report)

        self.tabs.addTab(w, "月報")

    def _refresh_months(self, select: str | None = None):
        months = sorted({ym(r.d) for r in self.records})
        if not months:
            months = [ym(date.today())]

        cur = select or (self.month.currentText() if self.month.count() else months[-1])

        self.month.blockSignals(True)
        self.month.clear()
        self.month.addItems(months)
        self.month.setCurrentText(cur if cur in months else months[-1])
        self.month.blockSignals(False)

    def _current_month(self):
        return self.month.currentText() or ym(date.today())

    def _month_stats(self, m: str):
        income = 0.0
        expense_total = 0.0
        by_cat = defaultdict(float)
        daily = defaultdict(float)

        for r in self.records:
            if ym(r.d) != m:
                continue
            if r.kind == "收入":
                income += r.amount
            else:
                expense_total += r.amount
                by_cat[r.category] += r.amount
                daily[r.d] += r.amount

        # 補齊類別（圖表穩）
        for cat in self.expense_categories:
            by_cat.setdefault(cat, 0.0)

        # 累計（支出）
        cum = []
        running = 0.0
        for d in sorted(daily.keys()):
            running += daily[d]
            cum.append(running)

        return income, expense_total, dict(by_cat), cum

    def _refresh_add_chart(self):
        m = self._current_month()
        _, _, by_cat, cum = self._month_stats(m)
        plot_monthly(by_cat, cum, self.canvas_add, m, note="（記帳頁）")

    def _refresh_report(self):
        m = self._current_month()
        income, expense_total, by_cat, cum = self._month_stats(m)
        balance = income - expense_total

        near, over = check_budget(by_cat, self.budgets, near_threshold=0.8)

        if over:
            warn_text = "⛔ 超支：\n" + "\n".join(over)
        elif near:
            warn_text = "⚠ 接近超支：\n" + "\n".join(near)
        else:
            warn_text = "✅ 預算正常"

        self.summary.setText(
            f"📅 月份：{m}\n"
            f"💰 本月收入：$ {income:,.0f}\n"
            f"💸 本月支出：$ {expense_total:,.0f}\n"
            f"📌 本月結餘：$ {balance:,.0f}\n\n"
            f"{warn_text}"
        )

        plot_monthly(by_cat, cum, self.canvas_report, m, note="（月報）")

    def _show_budget_alert_for_month(self, m: str):
        _, _, by_cat, _ = self._month_stats(m)
        near, over = check_budget(by_cat, self.budgets, near_threshold=0.8)
        if over:
            QMessageBox.critical(self, "超支警示", "【超支】\n" + "\n".join(over))
        elif near:
            QMessageBox.warning(self, "接近超支", "【接近超支】\n" + "\n".join(near))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = App()
    w.show()
    sys.exit(app.exec_())
