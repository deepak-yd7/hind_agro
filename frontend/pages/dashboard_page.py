from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGridLayout, QScrollArea, QPushButton, QSizePolicy,
    QDateEdit, QComboBox
)
from PyQt6.QtCore import Qt, QDate
from backend.realtime import db_signals
import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from datetime import date, timedelta

# ── Colours ───────────────────────────────────────────────────────────────────
GREEN_DARK   = "#1E3A1E"
GREEN_MID    = "#2D7A2D"
GREEN_LIGHT  = "#EAF3E4"
CHART_BG     = "#FFFFFF"
GRID_COLOR   = "#E8F0E8"

CHART_COLORS = ["#2D7A2D","#4A9A4A","#27AE60","#1ABC9C",
                "#2980B9","#8E44AD","#E67E22","#C0392B"]
STATUS_COLORS = {
    "Pending":"#E67E22","Confirmed":"#2980B9","Dispatched":"#8E44AD",
    "Delivered":"#27AE60","Cancelled":"#C0392B",
}
DELIVERY_COLORS = {
    "Pending":"#E67E22","Out for Delivery":"#2980B9",
    "Delivered":"#27AE60","Failed":"#C0392B",
}

PAGE_STYLE = """
QWidget#page      { background-color: #F5F7F2; }
QFrame#card       { background:white; border-radius:12px; border:1px solid #E0EAD8; }
QFrame#chart_card { background:white; border-radius:12px; border:1px solid #E0EAD8; }
QFrame#filter_bar { background:white; border-radius:10px; border:1px solid #D8ECD0; }
QLabel#page_title { font-size:26px; font-weight:bold; color:#1E3A1E; }
QLabel#page_sub   { font-size:13px; color:#7A9A7A; }
QLabel#chart_title{ font-size:14px; font-weight:bold; color:#1E3A1E; padding:4px 0; }
QLabel#filter_lbl { font-size:12px; font-weight:bold; color:#2D4A2D; }

QPushButton#preset_btn {
    background:#EAF3E4; color:#2D5A2D;
    border:1.5px solid #C8DFC0; border-radius:6px;
    padding:5px 13px; font-size:12px; font-weight:bold;
}
QPushButton#preset_btn:hover { background:#D0E8C8; }
QPushButton#preset_btn[active=true] {
    background:#2D4A2D; color:white; border:1.5px solid #2D4A2D;
}
QPushButton#apply_btn {
    background:#1E5C1E; color:white; border:none;
    border-radius:7px; padding:7px 20px; font-size:13px; font-weight:bold;
}
QPushButton#apply_btn:hover  { background:#2E7D2E; }
QPushButton#apply_btn:pressed{ background:#144014; }
QPushButton#refresh_btn {
    background:#2D4A2D; color:white; border:none;
    border-radius:7px; padding:7px 18px; font-size:13px; font-weight:bold;
}
QPushButton#refresh_btn:hover { background:#3D6B3D; }
QDateEdit {
    border:1.5px solid #C8DFC0; border-radius:6px;
    padding:5px 10px; font-size:12px; background:white; color:#1A3A1A;
}
QDateEdit:focus { border:1.5px solid #2D7A2D; }
QDateEdit::drop-down { border:none; width:20px; }
QComboBox#group_combo {
    border:1.5px solid #C8DFC0; border-radius:6px;
    padding:5px 10px; font-size:12px; background:white; color:#1A3A1A;
}
QComboBox#group_combo:focus { border:1.5px solid #2D7A2D; }
QComboBox#group_combo QAbstractItemView {
    background:white;
    color:#111111;
    selection-background-color:#D6EDD6;
    selection-color:#111111;
}
"""

# ── Preset date ranges ────────────────────────────────────────────────────────
def _preset_range(key: str):
    today = date.today()
    if key == "today":      return today, today
    if key == "yesterday":  y = today - timedelta(days=1); return y, y
    if key == "7d":         return today - timedelta(days=6), today
    if key == "14d":        return today - timedelta(days=13), today
    if key == "30d":        return today - timedelta(days=29), today
    if key == "this_month": return today.replace(day=1), today
    if key == "last_month":
        first = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        last  = today.replace(day=1) - timedelta(days=1)
        return first, last
    if key == "3m":         return today - timedelta(days=89), today
    if key == "6m":         return today - timedelta(days=179), today
    if key == "this_year":  return today.replace(month=1, day=1), today
    return today - timedelta(days=29), today

PRESETS = [
    ("Today",        "today"),
    ("Yesterday",    "yesterday"),
    ("Last 7 Days",  "7d"),
    ("Last 14 Days", "14d"),
    ("Last 30 Days", "30d"),
    ("This Month",   "this_month"),
    ("Last Month",   "last_month"),
    ("Last 3 Months","3m"),
    ("Last 6 Months","6m"),
    ("This Year",    "this_year"),
]

# ── Chart builders ─────────────────────────────────────────────────────────────
def make_stat_card(icon, label, value, color="#2D4A2D"):
    card = QFrame(); card.setObjectName("card"); card.setMinimumHeight(110)
    lay  = QVBoxLayout(card); lay.setContentsMargins(20, 14, 20, 14)
    top  = QHBoxLayout()
    icon_lbl = QLabel(icon); icon_lbl.setStyleSheet("font-size:26px;")
    top.addWidget(icon_lbl); top.addStretch(); lay.addLayout(top)
    val_lbl = QLabel(value)
    val_lbl.setStyleSheet(f"font-size:28px;font-weight:bold;color:{color};")
    lay.addWidget(val_lbl)
    lbl = QLabel(label); lbl.setStyleSheet("font-size:12px;color:#6B8F6B;")
    lay.addWidget(lbl)
    return card, val_lbl


def _base_fig(h=3.2):
    fig = Figure(figsize=(5, h), dpi=100, facecolor=CHART_BG)
    fig.subplots_adjust(left=0.13, right=0.97, top=0.90, bottom=0.20)
    return fig


def build_revenue_chart(rows, group_by="day"):
    fig = _base_fig(3.0); ax = fig.add_subplot(111); ax.set_facecolor(CHART_BG)
    if not rows:
        ax.text(0.5, 0.5, "No revenue data yet", ha="center", va="center",
                transform=ax.transAxes, color="#AAAAAA", fontsize=12)
        ax.axis("off"); return fig
    labels = [str(r[0]) for r in rows]
    values = [float(r[1]) for r in rows]
    x = range(len(labels))
    bars = ax.bar(x, values, color=GREEN_MID, width=0.55, zorder=3)
    ax.plot(list(x), values, color="#1D6A38", linewidth=2, marker="o", markersize=5, zorder=4)
    for bar, val in zip(bars, values):
        if val > 0:
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + max(values) * 0.02,
                    f"₹{val:,.0f}", ha="center", va="bottom",
                    fontsize=7, color=GREEN_DARK, fontweight="bold")
    ax.set_xticks(list(x))
    rot = 30 if len(labels) > 7 else 0
    ax.set_xticklabels(labels, fontsize=8, rotation=rot,
                       ha="right" if rot else "center")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"₹{v:,.0f}"))
    ax.tick_params(axis="y", labelsize=8)
    ax.set_ylabel("Revenue (₹)", fontsize=9, color="#555")
    ax.yaxis.grid(True, color=GRID_COLOR, linestyle="--", linewidth=0.7, zorder=0)
    ax.set_axisbelow(True)
    for sp in ax.spines.values(): sp.set_visible(False)
    ax.tick_params(length=0)
    return fig


def build_top_plants_chart(rows):
    fig = _base_fig(3.2); ax = fig.add_subplot(111); ax.set_facecolor(CHART_BG)
    if not rows:
        ax.text(0.5, 0.5, "No sales data yet", ha="center", va="center",
                transform=ax.transAxes, color="#AAAAAA", fontsize=12)
        ax.axis("off"); return fig
    names  = [r[0][:18] for r in rows]
    values = [int(r[1]) for r in rows]
    colors = CHART_COLORS[:len(names)]
    y = range(len(names))
    bars = ax.barh(list(y), values, color=colors, height=0.6, zorder=3)
    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + max(values) * 0.01,
                bar.get_y() + bar.get_height() / 2,
                str(val), va="center", fontsize=9,
                color=GREEN_DARK, fontweight="bold")
    ax.set_yticks(list(y)); ax.set_yticklabels(names, fontsize=9)
    ax.set_xlabel("Units Sold", fontsize=9, color="#555")
    ax.xaxis.grid(True, color=GRID_COLOR, linestyle="--", linewidth=0.7, zorder=0)
    ax.set_axisbelow(True)
    for sp in ax.spines.values(): sp.set_visible(False)
    ax.tick_params(length=0, labelsize=8)
    fig.subplots_adjust(left=0.30, right=0.93, top=0.90, bottom=0.14)
    return fig


def build_order_status_pie(data):
    fig = Figure(figsize=(4, 3.2), dpi=100, facecolor=CHART_BG)
    ax  = fig.add_subplot(111)
    filtered = {k: v for k, v in data.items() if v > 0}
    if not filtered:
        ax.text(0.5, 0.5, "No orders yet", ha="center", va="center",
                transform=ax.transAxes, color="#AAAAAA", fontsize=12)
        ax.axis("off"); return fig
    labels = list(filtered.keys()); values = list(filtered.values())
    colors = [STATUS_COLORS.get(l, "#888") for l in labels]
    _, _, autotexts = ax.pie(
        values, colors=colors, explode=[0.04] * len(labels),
        autopct=lambda p: f"{p:.0f}%" if p > 5 else "",
        pctdistance=0.75, startangle=140,
        wedgeprops={"linewidth": 1.5, "edgecolor": "white"})
    for at in autotexts:
        at.set_fontsize(9); at.set_color("white"); at.set_fontweight("bold")
    patches = [mpatches.Patch(color=c, label=f"{l} ({v})")
               for l, v, c in zip(labels, values, colors)]
    ax.legend(handles=patches, loc="lower center",
              bbox_to_anchor=(0.5, -0.20), ncol=3, fontsize=8, frameon=False)
    fig.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.24)
    return fig


def build_delivery_pie(data):
    fig = Figure(figsize=(4, 3.2), dpi=100, facecolor=CHART_BG)
    ax  = fig.add_subplot(111)
    filtered = {k: v for k, v in data.items() if v > 0}
    if not filtered:
        ax.text(0.5, 0.5, "No deliveries yet", ha="center", va="center",
                transform=ax.transAxes, color="#AAAAAA", fontsize=12)
        ax.axis("off"); return fig
    labels = list(filtered.keys()); values = list(filtered.values())
    colors = [DELIVERY_COLORS.get(l, "#888") for l in labels]
    ax.pie(values, colors=colors, explode=[0.04] * len(labels),
           autopct=lambda p: f"{p:.0f}%" if p > 5 else "",
           pctdistance=0.78, startangle=90,
           wedgeprops={"linewidth": 1.5, "edgecolor": "white", "width": 0.65})
    ax.text(0, 0, f"{sum(values)}\ndeliveries", ha="center", va="center",
            fontsize=9, color=GREEN_DARK, fontweight="bold")
    patches = [mpatches.Patch(color=c, label=f"{l} ({v})")
               for l, v, c in zip(labels, values, colors)]
    ax.legend(handles=patches, loc="lower center",
              bbox_to_anchor=(0.5, -0.20), ncol=2, fontsize=8, frameon=False)
    fig.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.24)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
#  Dashboard Page
# ─────────────────────────────────────────────────────────────────────────────
class DashboardPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("page")
        self.setStyleSheet(PAGE_STYLE)

        # State
        today             = date.today()
        self._from_date   = today - timedelta(days=29)
        self._to_date     = today
        self._active_preset = "30d"
        self._group_by    = "day"

        scroll = QScrollArea()
        scroll.setWidgetResizable(False)

        # Enable horizontal + vertical scrollbars
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background:transparent;")

        content = QWidget()
        content.setStyleSheet("""background-color: #F5FAF1;""")

        # IMPORTANT → prevents compression
        content.setMinimumWidth(1450)
        main = QVBoxLayout(content)
        main.setContentsMargins(32, 28, 32, 28); main.setSpacing(18)

        # ── Page header ───────────────────────────────────────────────────────
        hdr = QHBoxLayout()
        tc  = QVBoxLayout()
        title = QLabel("Dashboard"); title.setObjectName("page_title")
        sub   = QLabel("Live overview of your business performance.")
        sub.setObjectName("page_sub")
        tc.addWidget(title); tc.addWidget(sub)
        hdr.addLayout(tc); hdr.addStretch()

        refresh_btn = QPushButton("↻  Refresh")
        refresh_btn.setObjectName("refresh_btn")
        refresh_btn.setFixedHeight(34)
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.clicked.connect(self.load_data)
        hdr.addWidget(refresh_btn)
        main.addLayout(hdr)

        # ── Filter bar ────────────────────────────────────────────────────────
        filter_card = QFrame(); filter_card.setObjectName("filter_bar")
        filter_lay  = QVBoxLayout(filter_card)
        filter_lay.setContentsMargins(18, 14, 18, 14); filter_lay.setSpacing(10)

        # Preset buttons row
        preset_row = QHBoxLayout(); preset_row.setSpacing(6)
        fl = QLabel("Quick Filter:"); fl.setObjectName("filter_lbl")
        preset_row.addWidget(fl)
        self._preset_btns = {}
        for label, key in PRESETS:
            btn = QPushButton(label)
            btn.setObjectName("preset_btn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(30)
            btn.setProperty("active", key == self._active_preset)
            btn.clicked.connect(lambda _, k=key: self._apply_preset(k))
            preset_row.addWidget(btn)
            self._preset_btns[key] = btn
        preset_row.addStretch()
        filter_lay.addLayout(preset_row)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color:#E0EAD8;"); filter_lay.addWidget(sep)

        # Custom date range row
        custom_row = QHBoxLayout(); custom_row.setSpacing(12)
        dl = QLabel("Custom Range:"); dl.setObjectName("filter_lbl")
        custom_row.addWidget(dl)

        from_lbl = QLabel("From"); from_lbl.setStyleSheet("font-size:12px;color:#7A9A7A;")
        self._from_edit = QDateEdit()
        self._from_edit.setCalendarPopup(True)
        self._from_edit.setDate(QDate(self._from_date.year,
                                      self._from_date.month,
                                      self._from_date.day))
        self._from_edit.setFixedHeight(32)
        self._from_edit.setDisplayFormat("dd MMM yyyy")

        to_lbl = QLabel("To"); to_lbl.setStyleSheet("font-size:12px;color:#7A9A7A;")
        self._to_edit = QDateEdit()
        self._to_edit.setCalendarPopup(True)
        self._to_edit.setDate(QDate(self._to_date.year,
                                    self._to_date.month,
                                    self._to_date.day))
        self._to_edit.setFixedHeight(32)
        self._to_edit.setDisplayFormat("dd MMM yyyy")

        group_lbl = QLabel("Group By:"); group_lbl.setStyleSheet("font-size:12px;color:#7A9A7A;")
        self._group_combo = QComboBox()
        self._group_combo.setObjectName("group_combo")
        self._group_combo.setFixedHeight(32)
        self._group_combo.addItems(["Day", "Week", "Month"])
        self._group_combo.setCurrentText("Day")

        apply_btn = QPushButton("Apply Filter")
        apply_btn.setObjectName("apply_btn")
        apply_btn.setFixedHeight(34)
        apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        apply_btn.clicked.connect(self._apply_custom)

        custom_row.addWidget(from_lbl); custom_row.addWidget(self._from_edit)
        custom_row.addWidget(to_lbl);   custom_row.addWidget(self._to_edit)
        custom_row.addSpacing(8)
        custom_row.addWidget(group_lbl); custom_row.addWidget(self._group_combo)
        custom_row.addSpacing(8)
        custom_row.addWidget(apply_btn)
        custom_row.addStretch()
        filter_lay.addLayout(custom_row)

        self._active_lbl = QLabel("")
        self._active_lbl.setStyleSheet("font-size:11px;color:#4A7C4A;font-style:italic;")
        filter_lay.addWidget(self._active_lbl)
        main.addWidget(filter_card)

        # ── Stat cards ────────────────────────────────────────────────────────
        grid = QGridLayout(); grid.setSpacing(14)
        card1, self.lbl_plants    = make_stat_card("🪴", "Plants in Stock",   "…", "#2D7A2D")
        card2, self.lbl_customers = make_stat_card("👥", "Total Customers",   "…", "#1A5276")
        card3, self.lbl_pending   = make_stat_card("📦", "Pending Orders",    "…", "#7D6608")
        card4, self.lbl_unpaid    = make_stat_card("🧾", "Unpaid Invoices",   "…", "#922B21")
        card5, self.lbl_low_stock = make_stat_card("⚠️",  "Low Stock Lots",   "…", "#C0392B")
        card6, self.lbl_revenue   = make_stat_card("💰", "Revenue in Range",  "…", "#1D6A38")
        grid.addWidget(card1, 0, 0); grid.addWidget(card2, 0, 1); grid.addWidget(card3, 0, 2)
        grid.addWidget(card4, 1, 0); grid.addWidget(card5, 1, 1); grid.addWidget(card6, 1, 2)
        main.addLayout(grid)

        # ── Low stock warning ─────────────────────────────────────────────────
        self.low_stock_frame = QFrame()
        self.low_stock_frame.setStyleSheet(
            "background:#FFF8E7;border-radius:10px;border:1px solid #F0D080;")
        lsl = QVBoxLayout(self.low_stock_frame); lsl.setContentsMargins(16, 10, 16, 10)
        lst = QLabel("⚠️  Low Stock Production Lots")
        lst.setStyleSheet("font-weight:bold;color:#7D6608;font-size:13px;")
        self.low_stock_label = QLabel("—")
        self.low_stock_label.setStyleSheet("color:#5D4A00;font-size:12px;")
        self.low_stock_label.setWordWrap(True)
        lsl.addWidget(lst); lsl.addWidget(self.low_stock_label)
        main.addWidget(self.low_stock_frame)
        self.low_stock_frame.hide()

        # ── Charts ────────────────────────────────────────────────────────────
        row1 = QHBoxLayout(); row1.setSpacing(16)
        self._revenue_card  = self._make_chart_placeholder("📈  Revenue")
        self._orderpie_card = self._make_chart_placeholder("📊  Order Status")
        row1.addWidget(self._revenue_card,  stretch=3)
        row1.addWidget(self._orderpie_card, stretch=2)
        main.addLayout(row1)

        row2 = QHBoxLayout(); row2.setSpacing(16)
        self._plants_card   = self._make_chart_placeholder("🌿  Top Selling Plants")
        self._delivery_card = self._make_chart_placeholder("🚚  Delivery Status")
        row2.addWidget(self._plants_card,   stretch=3)
        row2.addWidget(self._delivery_card, stretch=2)
        main.addLayout(row2)

        main.addStretch()
        scroll.setWidget(content)
        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        # ── Real-time DB updates ──────────────────────────────────────────────
        db_signals.any_changed.connect(self._on_db_change)

        self._update_active_label()
        self.load_data()

    def _on_db_change(self, payload: str = ""):
        self.load_data()

    def _apply_preset(self, key: str):
        self._active_preset   = key
        self._from_date, self._to_date = _preset_range(key)
        self._from_edit.setDate(QDate(self._from_date.year,
                                      self._from_date.month,
                                      self._from_date.day))
        self._to_edit.setDate(QDate(self._to_date.year,
                                    self._to_date.month,
                                    self._to_date.day))
        days = (self._to_date - self._from_date).days
        if days <= 14:
            self._group_combo.setCurrentText("Day")
        elif days <= 90:
            self._group_combo.setCurrentText("Week")
        else:
            self._group_combo.setCurrentText("Month")
        for k, btn in self._preset_btns.items():
            btn.setProperty("active", k == key)
            btn.style().unpolish(btn); btn.style().polish(btn)
        self._update_active_label()
        self.load_data()

    def _apply_custom(self):
        qf = self._from_edit.date(); qt = self._to_edit.date()
        self._from_date = date(qf.year(), qf.month(), qf.day())
        self._to_date   = date(qt.year(), qt.month(), qt.day())
        if self._from_date > self._to_date:
            self._from_date, self._to_date = self._to_date, self._from_date
        self._active_preset = None
        for btn in self._preset_btns.values():
            btn.setProperty("active", False)
            btn.style().unpolish(btn); btn.style().polish(btn)
        self._group_by = self._group_combo.currentText().lower()
        self._update_active_label()
        self.load_data()

    def _update_active_label(self):
        self._group_by = self._group_combo.currentText().lower()
        days = (self._to_date - self._from_date).days + 1
        self._active_lbl.setText(
            f"Showing:  {self._from_date.strftime('%d %b %Y')}  →  "
            f"{self._to_date.strftime('%d %b %Y')}  "
            f"({days} day{'s' if days != 1 else ''})  ·  "
            f"Grouped by {self._group_combo.currentText()}"
        )

    def _make_chart_placeholder(self, title: str) -> QFrame:
        card = QFrame()
        card.setObjectName("chart_card")
        card.setMinimumHeight(280)
        card.setMinimumWidth(600)
        card.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Expanding
        )
        lay  = QVBoxLayout(card); lay.setContentsMargins(16, 14, 16, 14); lay.setSpacing(8)
        lbl  = QLabel(title); lbl.setObjectName("chart_title")
        lay.addWidget(lbl)
        ph = QLabel("Loading…")
        ph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ph.setStyleSheet("color:#AAAAAA;font-size:13px;")
        lay.addWidget(ph, stretch=1)
        card._title_lbl = lbl
        card._body_lay  = lay
        return card

    def _put_chart(self, card: QFrame, fig: Figure):
        lay = card._body_lay
        while lay.count() > 1:
            item = lay.takeAt(1)
            if item.widget():
                item.widget().deleteLater()
        canvas = FigureCanvas(fig)
        canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        lay.addWidget(canvas, stretch=1)

    def _sql_trunc(self):
        g = self._group_by
        if g == "day":
            return "day", "TO_CHAR(DATE_TRUNC('day',order_date),'DD Mon YY')", \
                "DATE_TRUNC('day',order_date)"
        if g == "week":
            return "week", "TO_CHAR(DATE_TRUNC('week',order_date),'DD Mon YY')", \
                "DATE_TRUNC('week',order_date)"
        return "month", "TO_CHAR(DATE_TRUNC('month',order_date),'Mon YYYY')", \
            "DATE_TRUNC('month',order_date)"

    # ── Data loading ───────────────────────────────────────────────────────────
    def load_data(self):
        self._update_active_label()
        try:
            from backend.database import get_connection
            with get_connection() as conn:
                cur = conn.cursor()
                self._load_stats(cur)
                self._load_revenue(cur)
                self._load_top_plants(cur)
                self._load_order_pie(cur)
                self._load_delivery_pie(cur)
        except Exception as e:
            for lbl in [self.lbl_plants, self.lbl_customers, self.lbl_pending,
                        self.lbl_unpaid, self.lbl_low_stock, self.lbl_revenue]:
                lbl.setText("—")
            print(f"[Dashboard] DB error: {e}")

    def _load_stats(self, cur):
        # 1. Total Plants across all Production Lots
        cur.execute("SELECT COALESCE(SUM(quantity), 0) FROM production_lots")
        self.lbl_plants.setText(f"{int(cur.fetchone()[0]):,}")

        cur.execute("SELECT COUNT(*) FROM customers")
        self.lbl_customers.setText(str(cur.fetchone()[0]))

        cur.execute("SELECT COUNT(*) FROM orders WHERE status='Pending'")
        self.lbl_pending.setText(str(cur.fetchone()[0]))

        cur.execute("SELECT COUNT(*) FROM invoices WHERE paid=FALSE")
        self.lbl_unpaid.setText(str(cur.fetchone()[0]))

        # 2. Low Stock Alerts (using a fixed threshold of 50 for lots)
        low_stock_threshold = 50
        cur.execute("""
            SELECT COUNT(*) FROM production_lots 
            WHERE quantity > 0 AND quantity <= %s
        """, (low_stock_threshold,))
        low = cur.fetchone()[0]
        self.lbl_low_stock.setText(str(low))

        cur.execute("""
            SELECT COALESCE(SUM(total_amount), 0) FROM orders
            WHERE status != 'Cancelled'
              AND DATE(order_date) BETWEEN %s AND %s
        """, (self._from_date, self._to_date))
        rev = cur.fetchone()[0]
        self.lbl_revenue.setText(f"{float(rev):,.0f}")

        # Update the UI warning panel for Low Stock
        if low > 0:
            cur.execute("""
                SELECT plant_name, lot_number, quantity
                FROM production_lots 
                WHERE quantity > 0 AND quantity <= %s
                ORDER BY quantity ASC LIMIT 10
            """, (low_stock_threshold,))
            lines = [f"• {r[0]} (Lot: {r[1]})  —  {r[2]} left (min threshold: {low_stock_threshold})"
                     for r in cur.fetchall()]
            self.low_stock_label.setText("\n".join(lines))
            self.low_stock_frame.show()
        else:
            self.low_stock_frame.hide()

    def _load_revenue(self, cur):
        _, lbl_expr, trunc_expr = self._sql_trunc()
        cur.execute(f"""
            SELECT {lbl_expr}, COALESCE(SUM(total_amount), 0)
            FROM orders
            WHERE status != 'Cancelled'
              AND DATE(order_date) BETWEEN %s AND %s
            GROUP BY {trunc_expr}
            ORDER BY {trunc_expr}
        """, (self._from_date, self._to_date))
        rows = cur.fetchall()
        label = (f"📈  Revenue  [{self._from_date.strftime('%d %b')} – "
                 f"{self._to_date.strftime('%d %b %Y')}]")
        self._revenue_card._title_lbl.setText(label)
        self._put_chart(self._revenue_card, build_revenue_chart(rows, self._group_by))

    def _load_top_plants(self, cur):
        # UPDATED: Now joins with production_lots instead of plants
        cur.execute("""
            SELECT pl.plant_name, COALESCE(SUM(oi.quantity), 0) AS sold
            FROM production_lots pl
            JOIN order_items oi ON pl.id = oi.production_lot_id
            JOIN orders o ON oi.order_id = o.id
            WHERE o.status != 'Cancelled'
              AND DATE(o.order_date) BETWEEN %s AND %s
            GROUP BY pl.plant_name
            ORDER BY sold DESC LIMIT 8
        """, (self._from_date, self._to_date))
        rows = cur.fetchall()
        self._plants_card._title_lbl.setText(
            f"🌿  Top Selling Plants  [{self._from_date.strftime('%d %b')} – "
            f"{self._to_date.strftime('%d %b %Y')}]")
        self._put_chart(self._plants_card, build_top_plants_chart(rows))

    def _load_order_pie(self, cur):
        cur.execute("""
            SELECT status, COUNT(*) FROM orders
            WHERE DATE(order_date) BETWEEN %s AND %s
            GROUP BY status
        """, (self._from_date, self._to_date))
        data = {r[0]: r[1] for r in cur.fetchall()}
        for s in ["Pending", "Confirmed", "Dispatched", "Delivered", "Cancelled"]:
            data.setdefault(s, 0)
        self._orderpie_card._title_lbl.setText(
            f"📊  Order Status  [{self._from_date.strftime('%d %b')} – "
            f"{self._to_date.strftime('%d %b %Y')}]")
        self._put_chart(self._orderpie_card, build_order_status_pie(data))

    def _load_delivery_pie(self, cur):
        cur.execute("""
            SELECT COALESCE(delivery_status, 'Pending'), COUNT(*)
            FROM orders
            WHERE status NOT IN ('Cancelled', 'Pending')
              AND DATE(order_date) BETWEEN %s AND %s
            GROUP BY delivery_status
        """, (self._from_date, self._to_date))
        data = {r[0]: r[1] for r in cur.fetchall()}
        for s in ["Pending", "Out for Delivery", "Delivered", "Failed"]:
            data.setdefault(s, 0)
        self._delivery_card._title_lbl.setText(
            f"🚚  Delivery Status  [{self._from_date.strftime('%d %b')} – "
            f"{self._to_date.strftime('%d %b %Y')}]")
        self._put_chart(self._delivery_card, build_delivery_pie(data))