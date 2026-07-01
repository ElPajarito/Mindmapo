#!/usr/bin/env python3
"""MindMapo — a lively, interactive mind map for pentest engagements.

Run:  python3 main.py
"""

import json
import sys

from PySide6.QtCore import Qt, QPointF, Signal
from PySide6.QtGui import QAction, QKeySequence, QFont, QColor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QComboBox, QLineEdit, QPlainTextEdit,
    QFileDialog, QToolBar, QSizePolicy, QGraphicsView, QMenu, QToolButton,
    QDockWidget, QInputDialog,
)

from categories import CATEGORIES, get_category, THEME
from node import MindNode
from scene import MindScene, MindView
from minimap import Minimap
from idea_tracker import IdeaTracker


def style_sheet():
    t = THEME
    return f"""
    QMainWindow, QWidget {{
        background: {t['bg_bottom']};
        color: {t['text']};
        font-family: 'Segoe UI', 'Ubuntu', sans-serif;
        font-size: 13px;
    }}
    #Sidebar, #Inspector {{
        background: {t['panel']};
        border: 1px solid {t['border']};
        border-radius: 16px;
    }}
    #PanelTitle {{
        color: {t['text']};
        font-size: 15px;
        font-weight: 800;
        padding: 4px 2px;
    }}
    #SectionLabel {{
        color: {t['text_dim']};
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 1px;
        padding: 6px 2px 2px 2px;
    }}
    #PaletteToggle {{
        background: {t['panel_alt']};
        border: 1px solid {t['border']};
        border-radius: 11px;
        padding: 9px 10px;
        text-align: left;
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 1px;
        color: {t['text_dim']};
    }}
    #PaletteToggle:hover {{ background: #243056; color: {t['text']}; }}
    QPushButton.cat {{
        text-align: left;
        padding: 9px 12px;
        border: none;
        border-radius: 12px;
        font-weight: 700;
        font-size: 13px;
        color: #0c1020;
    }}
    QPushButton.cat:hover {{
        padding-left: 16px;
    }}
    QPushButton#tool {{
        background: {t['panel_alt']};
        border: 1px solid {t['border']};
        border-radius: 11px;
        padding: 9px 12px;
        font-weight: 700;
        color: {t['text']};
    }}
    QPushButton#tool:hover {{ background: #243056; }}
    QPushButton#tool:checked {{
        background: {t['accent']};
        color: #221a00;
        border: 1px solid {t['accent']};
    }}
    QToolButton#tool {{
        background: {t['panel_alt']};
        border: 1px solid {t['border']};
        border-radius: 11px;
        padding: 8px 12px;
        font-weight: 700;
        color: {t['text']};
    }}
    QToolButton#tool:hover {{ background: #243056; }}
    QToolButton#tool::menu-indicator {{ image: none; width: 0; }}
    QMenu {{
        background: {t['panel_alt']};
        border: 1px solid {t['border']};
        border-radius: 10px;
        padding: 6px;
    }}
    QMenu::item {{ padding: 7px 22px; border-radius: 7px; }}
    QMenu::item:selected {{ background: #243056; }}
    QMenu::separator {{ height: 1px; background: {t['border']}; margin: 5px 8px; }}
    QLineEdit#search {{
        background: {t['panel_alt']};
        border: 1px solid {t['border']};
        border-radius: 11px;
        padding: 8px 12px;
        min-width: 190px;
        color: {t['text']};
    }}
    QLineEdit#search:focus {{ border: 1px solid {t['accent']}; }}
    #IdeaPanel {{
        background: rgba(14, 19, 38, 0.92);
        border: 1px solid {t['border']};
        border-radius: 14px;
    }}
    #IdeaHeader {{
        background: transparent;
        border: none;
        text-align: left;
        font-weight: 800;
        font-size: 13px;
        color: {t['text']};
        padding: 6px 8px;
    }}
    #IdeaHeader:hover {{ color: {t['accent']}; }}
    #IdeaAdd {{
        background: {t['panel_alt']};
        border: 1px solid {t['border']};
        border-radius: 9px;
        padding: 6px 9px;
        color: {t['text']};
    }}
    #IdeaAdd:focus {{ border: 1px solid {t['accent']}; }}
    #IdeaScroll {{ border: none; background: transparent; }}
    #IdeaEmpty {{ color: {t['text_dim']}; font-size: 11px; padding: 6px; }}
    #IdeaDel {{
        background: transparent; border: none; color: {t['text_dim']};
        font-size: 12px; padding: 0 4px;
    }}
    #IdeaDel:hover {{ color: #ff9bb5; }}
    QCheckBox {{ spacing: 7px; }}
    QCheckBox::indicator {{
        width: 16px; height: 16px; border-radius: 5px;
        border: 1px solid {t['border']}; background: {t['panel_alt']};
    }}
    QCheckBox::indicator:hover {{ border: 1px solid {t['accent']}; }}
    QCheckBox::indicator:checked {{
        background: {t['accent']}; border: 1px solid {t['accent']};
    }}
    QPushButton#danger {{
        background: #3a1320; border: 1px solid #6b2440;
        border-radius: 11px; padding: 9px 12px; font-weight: 700; color: #ff9bb5;
    }}
    QPushButton#danger:hover {{ background: #54192e; }}
    QPushButton#layoutBtn {{
        background: {t['panel_alt']}; border: 1px solid {t['border']};
        border-radius: 8px; min-width: 26px; padding: 4px 7px;
        font-size: 14px; font-weight: 700; color: {t['text']};
    }}
    QPushButton#layoutBtn:hover {{ background: #243056; color: {t['accent']}; }}
    QDockWidget {{
        color: {t['text']};
        font-weight: 800;
        titlebar-close-icon: none;
        titlebar-normal-icon: none;
    }}
    QDockWidget::title {{
        background: {t['panel']};
        padding: 8px 12px;
        border: 1px solid {t['border']};
        border-top-left-radius: 12px;
        border-top-right-radius: 12px;
        text-align: left;
    }}
    QDockWidget::close-button, QDockWidget::float-button {{
        background: {t['panel_alt']};
        border: 1px solid {t['border']};
        border-radius: 6px;
        padding: 2px;
    }}
    QDockWidget::close-button:hover {{ background: #54192e; }}
    QDockWidget::float-button:hover {{ background: #243056; }}
    #MapTabs {{
        background: {t['panel']};
        border: 1px solid {t['border']};
        border-radius: 14px;
    }}
    #TabScroll {{ background: transparent; border: none; }}
    #TabPill {{
        background: {t['panel_alt']};
        border: 1px solid {t['border']};
        border-radius: 11px;
    }}
    #TabPill:hover {{ border: 1px solid {t['accent']}; }}
    #TabPill[active="true"] {{
        background: {t['accent']};
        border: 1px solid {t['accent']};
    }}
    #TabLabel {{ color: {t['text']}; font-weight: 700; background: transparent; }}
    #TabPill[active="true"] #TabLabel {{ color: #221a00; font-weight: 800; }}
    #TabClose {{
        background: transparent; border: none; color: {t['text_dim']};
        font-size: 12px; font-weight: 800; padding: 0 2px;
    }}
    #TabClose:hover {{ color: #ff9bb5; }}
    #TabPill[active="true"] #TabClose {{ color: #6b4a00; }}
    #TabPill[active="true"] #TabClose:hover {{ color: #7a1224; }}
    #TabAdd, #TabCollapse {{
        background: {t['panel_alt']}; border: 1px solid {t['border']};
        border-radius: 11px; padding: 8px 12px; font-weight: 700; color: {t['text']};
    }}
    #TabAdd:hover, #TabCollapse:hover {{ background: #243056; color: {t['accent']}; }}
    #TabMini {{ color: {t['text_dim']}; font-weight: 800; padding: 0 8px; }}
    QLineEdit, QPlainTextEdit, QComboBox {{
        background: {t['panel_alt']};
        border: 1px solid {t['border']};
        border-radius: 10px;
        padding: 7px 9px;
        color: {t['text']};
        selection-background-color: {t['accent']};
    }}
    QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus {{
        border: 1px solid {t['accent']};
    }}
    QComboBox::drop-down {{ border: none; width: 22px; }}
    QComboBox QAbstractItemView {{
        background: {t['panel_alt']};
        border: 1px solid {t['border']};
        selection-background-color: #243056;
        outline: none;
    }}
    QToolBar {{
        background: {t['panel']};
        border-bottom: 1px solid {t['border']};
        padding: 6px 10px;
        spacing: 8px;
    }}
    QLabel#brand {{
        font-size: 18px; font-weight: 900; color: {t['text']};
        padding: 0 8px;
    }}
    QLabel#brandSub {{ color: {t['accent']}; font-weight: 900; }}
    QStatusBar {{ background: {t['panel']}; color: {t['text_dim']}; }}
    QScrollArea {{ border: none; background: transparent; }}
    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: {t['border']}; border-radius: 5px; min-height: 30px; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
    """


class Inspector(QFrame):
    """Edit panel for the selected node.

    Re-flows between a vertical (docked left/right) and horizontal (docked
    top/bottom) arrangement, and can be torn off into a floating window.
    """

    layoutVertical = Signal()
    layoutHorizontal = Signal()
    layoutFloat = Signal()

    def __init__(self, scene, parent=None):
        super().__init__(parent)
        self.setObjectName("Inspector")
        self.scene = scene
        self.node = None
        self.vertical = True
        self.setMinimumWidth(150)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 12, 14, 14)
        outer.setSpacing(10)

        # ---- layout-mode controls (always at the top) ----
        controls = QHBoxLayout()
        controls.setSpacing(6)
        controls.addWidget(self._label("LAYOUT", "SectionLabel"))
        controls.addStretch(1)
        for text, tip, sig in (
            ("⬍", "Vertical (dock left/right)", self.layoutVertical),
            ("⬌", "Horizontal (dock top/bottom)", self.layoutHorizontal),
            ("⧉", "Float as window", self.layoutFloat),
        ):
            b = QPushButton(text)
            b.setObjectName("layoutBtn")
            b.setToolTip(tip)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(sig.emit)
            controls.addWidget(b)
        outer.addLayout(controls)

        # ---- fields (their arrangement is swapped on orientation change) ----
        self.title_lbl = QLabel("No node selected")
        self.title_lbl.setObjectName("PanelTitle")
        self.title_lbl.setWordWrap(True)
        self.title_lbl.setMaximumWidth(360)

        self.title_edit = QLineEdit()
        self.title_edit.textEdited.connect(self._on_title)
        self.g_title = self._group("TITLE", self.title_edit)

        self.cat_combo = QComboBox()
        for key, cat in CATEGORIES.items():
            self.cat_combo.addItem(f"{cat.emoji}  {cat.label}", key)
        self.cat_combo.currentIndexChanged.connect(self._on_category)
        self.g_cat = self._group("CATEGORY", self.cat_combo)

        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setPlaceholderText("Creds, ports, payloads, observations…")
        self.notes_edit.textChanged.connect(self._on_notes)
        self.g_notes = self._group("INTEL / NOTES", self.notes_edit)

        self.del_btn = QPushButton("\U0001F5D1  Delete node")
        self.del_btn.setObjectName("danger")
        self.del_btn.clicked.connect(self._delete)

        self.fields = QWidget()
        outer.addWidget(self.fields, 1)
        self.set_orientation(True)

        self._busy = False
        self.set_node(None)

    def _label(self, text, obj):
        l = QLabel(text)
        l.setObjectName(obj)
        return l

    def _group(self, label, widget):
        g = QWidget()
        gl = QVBoxLayout(g)
        gl.setContentsMargins(0, 0, 0, 0)
        gl.setSpacing(4)
        gl.addWidget(self._label(label, "SectionLabel"))
        gl.addWidget(widget, 1)
        return g

    def set_orientation(self, vertical):
        """Re-pack the field widgets into a vertical or horizontal box."""
        self.vertical = vertical
        units = (self.title_lbl, self.g_title, self.g_cat, self.g_notes, self.del_btn)

        old = self.fields.layout()
        if old is not None:
            while old.count():
                w = old.takeAt(0).widget()
                if w is not None:
                    w.setParent(None)
            QWidget().setLayout(old)        # dispose the now-empty old layout

        new = QVBoxLayout() if vertical else QHBoxLayout()
        new.setContentsMargins(0, 0, 0, 0)
        new.setSpacing(10)
        for w in units:
            new.addWidget(w, 1 if w is self.g_notes else 0)
        if not vertical:
            new.setAlignment(self.del_btn, Qt.AlignTop)
        self.fields.setLayout(new)
        for w in units:
            w.show()

    def set_node(self, node):
        self._busy = True
        self.node = node
        enabled = node is not None
        for w in (self.title_edit, self.cat_combo, self.notes_edit, self.del_btn):
            w.setEnabled(enabled)
        if node is None:
            self.title_lbl.setText("No node selected")
            self.title_edit.clear()
            self.notes_edit.setPlainText("")
        else:
            cat = get_category(node.category)
            self.title_lbl.setText(f"{cat.emoji}  {node.title}")
            self.title_edit.setText(node.title)
            self.notes_edit.setPlainText(node.notes)
            idx = self.cat_combo.findData(node.category)
            if idx >= 0:
                self.cat_combo.setCurrentIndex(idx)
        self._busy = False

    def _on_title(self, text):
        if self._busy or not self.node:
            return
        self.node.set_title(text)
        cat = get_category(self.node.category)
        self.title_lbl.setText(f"{cat.emoji}  {text}")

    def _on_category(self):
        if self._busy or not self.node:
            return
        self.node.set_category(self.cat_combo.currentData())
        cat = get_category(self.node.category)
        self.title_lbl.setText(f"{cat.emoji}  {self.node.title}")

    def _on_notes(self):
        if self._busy or not self.node:
            return
        self.node.notes = self.notes_edit.toPlainText()

    def _delete(self):
        if self.node:
            self.scene.delete_node(self.node)


class Sidebar(QFrame):
    """Left palette of pentest categories + quick actions."""

    EXPANDED_W = 220
    COLLAPSED_W = 48

    def __init__(self, on_add, parent=None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(self.EXPANDED_W)
        self.on_add = on_add
        self.expanded = True

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 10, 8, 10)
        outer.setSpacing(8)

        self.toggle_btn = QPushButton()
        self.toggle_btn.setObjectName("PaletteToggle")
        self.toggle_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_btn.clicked.connect(self.toggle)
        outer.addWidget(self.toggle_btn)

        # Everything below the header hides when collapsed.
        self.body = QWidget()
        body_lay = QVBoxLayout(self.body)
        body_lay.setContentsMargins(6, 0, 6, 0)
        body_lay.setSpacing(6)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        holder = QWidget()
        col = QVBoxLayout(holder)
        col.setContentsMargins(0, 0, 4, 0)
        col.setSpacing(7)
        for key, cat in CATEGORIES.items():
            col.addWidget(self._cat_button(key, cat))
        col.addStretch(1)
        scroll.setWidget(holder)
        body_lay.addWidget(scroll, 1)

        hint = QLabel("Tip: right-click a node to add a child.\nDrag to move • Wheel to zoom • Alt-drag to pan")
        hint.setObjectName("SectionLabel")
        hint.setWordWrap(True)
        body_lay.addWidget(hint)

        outer.addWidget(self.body, 1)
        self._apply_state()

    def toggle(self):
        self.expanded = not self.expanded
        self._apply_state()

    def _apply_state(self):
        self.body.setVisible(self.expanded)
        self.setFixedWidth(self.EXPANDED_W if self.expanded else self.COLLAPSED_W)
        if self.expanded:
            self.toggle_btn.setText("ADD A NODE      ▾")
            self.toggle_btn.setToolTip("Collapse palette")
            self.toggle_btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        else:
            # Make the whole slim strip one big clickable button so it's
            # impossible to miss when re-expanding.
            self.toggle_btn.setText("➕\n▸")
            self.toggle_btn.setToolTip("Expand palette")
            self.toggle_btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

    def _section(self, text):
        l = QLabel(text)
        l.setObjectName("SectionLabel")
        return l

    def _cat_button(self, key, cat):
        btn = QPushButton(f"{cat.emoji}   {cat.label}")
        btn.setProperty("class", "cat")
        btn.setCursor(Qt.PointingHandCursor)
        base = QColor(cat.color)
        btn.setStyleSheet(
            f"QPushButton{{text-align:left;padding:9px 12px;border:none;"
            f"border-radius:12px;font-weight:700;color:#0c1020;"
            f"background:{cat.color};}}"
            f"QPushButton:hover{{background:{base.lighter(115).name()};padding-left:16px;}}"
        )
        btn.clicked.connect(lambda _=False, k=key: self.on_add(k))
        return btn


class TabPill(QFrame):
    """A single map tab: click to switch, double-click to rename, ✕ to close."""

    clicked = Signal()
    doubleClicked = Signal()
    closeClicked = Signal()

    def __init__(self, text, active=False, closable=True, parent=None):
        super().__init__(parent)
        self.setObjectName("TabPill")
        self.setProperty("active", "true" if active else "false")
        self.setCursor(Qt.PointingHandCursor)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 6, 8, 6)
        lay.setSpacing(6)

        self.lbl = QLabel(text)
        self.lbl.setObjectName("TabLabel")
        self.lbl.setToolTip("Click to open · double-click to rename")
        lay.addWidget(self.lbl)

        if closable:
            x = QToolButton()
            x.setObjectName("TabClose")
            x.setText("✕")
            x.setCursor(Qt.PointingHandCursor)
            x.setToolTip("Close map")
            x.clicked.connect(lambda: self.closeClicked.emit())
            lay.addWidget(x)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(e)

    def mouseDoubleClickEvent(self, e):
        self.doubleClicked.emit()
        super().mouseDoubleClickEvent(e)


class MapTabs(QFrame):
    """Collapsible strip of tabs — one mind map per tab for the same asset."""

    switchRequested = Signal(int)
    addRequested = Signal()
    closeRequested = Signal(int)
    renameRequested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MapTabs")
        self.collapsed = False
        self._names = []
        self._active = 0

        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 6, 8, 6)
        lay.setSpacing(8)

        self.collapse_btn = QToolButton()
        self.collapse_btn.setObjectName("TabCollapse")
        self.collapse_btn.setCursor(Qt.PointingHandCursor)
        self.collapse_btn.clicked.connect(self._toggle_collapsed)
        lay.addWidget(self.collapse_btn)

        # Compact summary shown only while collapsed.
        self.mini = QLabel("")
        self.mini.setObjectName("TabMini")
        self.mini.setVisible(False)
        lay.addWidget(self.mini)

        # Horizontally-scrollable row of tab pills.
        self.scroll = QScrollArea()
        self.scroll.setObjectName("TabScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setFixedHeight(48)
        self.row_holder = QWidget()
        self.row = QHBoxLayout(self.row_holder)
        self.row.setContentsMargins(0, 0, 0, 0)
        self.row.setSpacing(6)
        self.row.addStretch(1)
        self.scroll.setWidget(self.row_holder)
        lay.addWidget(self.scroll, 1)

        self.add_btn = QToolButton()
        self.add_btn.setObjectName("TabAdd")
        self.add_btn.setText("➕  New map")
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.setToolTip("Add a new mind map for this asset")
        self.add_btn.clicked.connect(lambda: self.addRequested.emit())
        lay.addWidget(self.add_btn)

        self._update_collapse_btn()

    def _toggle_collapsed(self):
        self.collapsed = not self.collapsed
        self.scroll.setVisible(not self.collapsed)
        self.add_btn.setVisible(not self.collapsed)
        self.mini.setVisible(self.collapsed)
        self._update_collapse_btn()

    def _update_collapse_btn(self):
        self.collapse_btn.setText("\U0001F5C2 ▸" if self.collapsed else "\U0001F5C2 ▾")
        self.collapse_btn.setToolTip("Show map tabs" if self.collapsed else "Hide map tabs")

    def set_tabs(self, names, active):
        self._names = list(names)
        self._active = active
        while self.row.count() > 1:                 # keep the trailing stretch
            item = self.row.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)                   # remove immediately, not on next tick
                w.deleteLater()

        closable = len(names) > 1
        for i, name in enumerate(names):
            pill = TabPill(name, active=(i == active), closable=closable)
            pill.clicked.connect(lambda idx=i: self.switchRequested.emit(idx))
            pill.doubleClicked.connect(lambda idx=i: self.renameRequested.emit(idx))
            pill.closeClicked.connect(lambda idx=i: self.closeRequested.emit(idx))
            self.row.insertWidget(self.row.count() - 1, pill)

        cur = names[active] if 0 <= active < len(names) else ""
        self.mini.setText(f"\U0001F5C2  {cur}   ·   {len(names)} map(s)")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MindMapo — Pentest Mind Map")
        self.resize(1280, 820)
        self.current_file = None

        self.scene = MindScene(self)
        self.view = MindView(self.scene)
        self.view.setObjectName("Canvas")

        self.sidebar = Sidebar(self.add_from_palette)

        # Tab bar — several mind maps for the same asset.
        self.tabs = MapTabs()
        self.tabs.switchRequested.connect(self.switch_map)
        self.tabs.addRequested.connect(self.add_map)
        self.tabs.closeRequested.connect(self.close_map)
        self.tabs.renameRequested.connect(self.rename_map)

        central = QWidget()
        h = QHBoxLayout(central)
        h.setContentsMargins(12, 12, 12, 12)
        h.setSpacing(12)
        h.addWidget(self.sidebar)
        right = QWidget()
        col = QVBoxLayout(right)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(10)
        col.addWidget(self.tabs)
        col.addWidget(self.view, 1)
        h.addWidget(right, 1)
        self.setCentralWidget(central)

        # Each entry: {"name": str, "state": dict|None}. The active tab's data
        # lives in the live scene; "state" holds the serialized copy otherwise.
        self.maps = [{"name": "Map 1", "state": None}]
        self.active_map = 0

        # Inspector lives in a dock so it can be resized, re-docked
        # (vertical / horizontal) or torn off into a floating window.
        self.inspector = Inspector(self.scene)
        self.inspector_dock = QDockWidget("  \U0001F50D  Inspector", self)
        self.inspector_dock.setObjectName("InspectorDock")
        self.inspector_dock.setWidget(self.inspector)
        self.inspector_dock.setAllowedAreas(
            Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea
            | Qt.TopDockWidgetArea | Qt.BottomDockWidgetArea)
        self.inspector_dock.setFeatures(
            QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable
            | QDockWidget.DockWidgetClosable)
        self.addDockWidget(Qt.RightDockWidgetArea, self.inspector_dock)
        self.resizeDocks([self.inspector_dock], [300], Qt.Horizontal)
        self.inspector_dock.dockLocationChanged.connect(self._on_inspector_docked)
        self.inspector.layoutVertical.connect(
            lambda: self._dock_inspector(Qt.RightDockWidgetArea))
        self.inspector.layoutHorizontal.connect(
            lambda: self._dock_inspector(Qt.BottomDockWidgetArea))
        self.inspector.layoutFloat.connect(self._float_inspector)

        self._matches = []
        self._match_idx = -1

        self._build_toolbar()
        self.statusBar().showMessage("Ready. Add a node from the left to begin.")

        self.scene.selectionChanged.connect(self._sync_inspector)
        self.scene.selection_info_changed.connect(self._sync_inspector)
        self.scene.status_message.connect(self._on_status)

        self.minimap = Minimap(self.view)
        self.scene.changed.connect(lambda *_: self.minimap.update())
        self.ideas = IdeaTracker(self.view)

        self._make_sample_map()
        self._refresh_tabs()
        self.view.fit_all()

    def showEvent(self, event):
        super().showEvent(event)
        self.minimap.reposition()
        self.minimap.update()
        self.ideas.reposition()

    # ------------------------------------------------------------------ toolbar
    def _build_toolbar(self):
        tb = QToolBar()
        tb.setMovable(False)
        tb.setIconSize(tb.iconSize())
        self.addToolBar(tb)

        brand = QLabel("\U0001F344 MindMap")
        brand.setObjectName("brand")
        sub = QLabel("o")
        sub.setObjectName("brandSub")
        sub.setStyleSheet("font-size:18px;font-weight:900;")
        tb.addWidget(brand)
        tb.addWidget(sub)

        spacer1 = QWidget()
        spacer1.setFixedWidth(18)
        tb.addWidget(spacer1)

        tb.addWidget(self._tbtn("\U0001F4C4  New", self.new_map))
        tb.addWidget(self._tbtn("\U0001F4C2  Open", self.open_map))
        tb.addWidget(self._tbtn("\U0001F4BE  Save", self.save_map))

        tb.addWidget(self._menu_btn("\U0001F4D0  Layout", [
            ("✨  Auto-arrange (force)", self.auto_arrange),
            ("\U0001F333  Tree (layered)", self.layout_tree),
            ("\U0001F3CA  Swimlanes (by phase)", self.layout_swimlane),
        ]))
        tb.addWidget(self._menu_btn("\U0001F4E4  Export", [
            ("\U0001F5BC  Export PNG…", self.export_png),
            ("\U0001F4DD  Export Markdown…", self.export_markdown),
        ]))
        tb.addWidget(self._menu_btn("\U0001F50D  Inspector", [
            ("\U0001F441  Show / hide", self.toggle_inspector),
            ("⬍  Vertical (right)", lambda: self._dock_inspector(Qt.RightDockWidgetArea)),
            ("⬌  Horizontal (bottom)", lambda: self._dock_inspector(Qt.BottomDockWidgetArea)),
            ("⧉  Float window", self._float_inspector),
        ]))

        self.link_btn = self._tbtn("\U0001F517  Link mode", self.toggle_link, checkable=True)
        tb.addWidget(self.link_btn)

        stretch = QWidget()
        stretch.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tb.addWidget(stretch)

        self.search = QLineEdit()
        self.search.setObjectName("search")
        self.search.setPlaceholderText("\U0001F50D  Search nodes…  (Enter = next)")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.on_search)
        self.search.returnPressed.connect(self.next_match)
        tb.addWidget(self.search)

        tb.addWidget(self._tbtn("\U0001F50D  Fit", self.view.fit_all))
        tb.addWidget(self._tbtn("➕  Reset zoom", self.view.reset_zoom))

        # keyboard shortcuts
        self._shortcut("Ctrl+N", self.new_map)
        self._shortcut("Ctrl+O", self.open_map)
        self._shortcut("Ctrl+S", self.save_map)
        self._shortcut("L", self.link_btn.click)
        self._shortcut("Delete", self.scene.delete_selected)
        self._shortcut("Backspace", self.scene.delete_selected)
        self._shortcut("Escape", lambda: self._set_link(False))
        self._shortcut("Ctrl+0", self.view.fit_all)

    def _tbtn(self, text, slot, checkable=False):
        b = QPushButton(text)
        b.setObjectName("tool")
        b.setCursor(Qt.PointingHandCursor)
        b.setCheckable(checkable)
        b.clicked.connect(slot)
        return b

    def _menu_btn(self, text, items):
        b = QToolButton()
        b.setObjectName("tool")
        b.setText(text)
        b.setCursor(Qt.PointingHandCursor)
        b.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(b)
        for label, slot in items:
            menu.addAction(label, slot)
        b.setMenu(menu)
        return b

    def _shortcut(self, seq, slot):
        act = QAction(self)
        act.setShortcut(QKeySequence(seq))
        act.triggered.connect(slot)
        self.addAction(act)

    # ------------------------------------------------------------------ actions
    def add_from_palette(self, category):
        center = self.view.mapToScene(self.view.viewport().rect().center())
        node = self.scene.add_node(category, center - QPointF(75, 31))
        self.scene.clearSelection()
        node.setSelected(True)
        self.statusBar().showMessage(f"Added a {get_category(category).label} node.")

    def toggle_link(self):
        self._set_link(self.link_btn.isChecked())

    def _set_link(self, on):
        self.link_btn.setChecked(on)
        self.scene.set_link_mode(on)

    def auto_arrange(self):
        self.statusBar().showMessage("Auto-arranging…")
        self.scene.auto_arrange()
        self.view.fit_all()
        self.statusBar().showMessage("Auto-arranged.")

    def layout_tree(self):
        self.scene.tree_layout()
        self.view.fit_all()
        self.statusBar().showMessage("Tree layout applied.")

    def layout_swimlane(self):
        self.scene.swimlane_layout()
        self.view.fit_all()
        self.statusBar().showMessage("Swimlane layout applied — one lane per kill-chain phase.")

    # ----- map tabs
    def _refresh_tabs(self):
        self.tabs.set_tabs([m["name"] for m in self.maps], self.active_map)

    def _current_state(self):
        data = self.scene.to_dict()
        data["ideas"] = self.ideas.to_list()
        return data

    def _capture_active(self):
        self.maps[self.active_map]["state"] = self._current_state()

    def _load_state(self, state):
        state = state or {"nodes": [], "edges": [], "ideas": []}
        self.scene.from_dict(state)
        self.ideas.load(state.get("ideas", []))
        self.inspector.set_node(None)

    def _next_map_name(self):
        n = len(self.maps) + 1
        existing = {m["name"] for m in self.maps}
        while f"Map {n}" in existing:
            n += 1
        return f"Map {n}"

    def switch_map(self, index):
        if index == self.active_map or not (0 <= index < len(self.maps)):
            return
        self._capture_active()
        self.active_map = index
        self._load_state(self.maps[index]["state"])
        self._refresh_tabs()
        self.view.fit_all()
        self.statusBar().showMessage(f"Switched to “{self.maps[index]['name']}”.")

    def add_map(self):
        self._capture_active()
        self.maps.append({"name": self._next_map_name(),
                          "state": {"nodes": [], "edges": [], "ideas": []}})
        self.active_map = len(self.maps) - 1
        self._load_state(self.maps[self.active_map]["state"])
        self._refresh_tabs()
        self.view.fit_all()
        self.statusBar().showMessage(f"New map “{self.maps[self.active_map]['name']}” added.")

    def close_map(self, index):
        if not (0 <= index < len(self.maps)):
            return
        if len(self.maps) <= 1:
            self.statusBar().showMessage("At least one map is required.")
            return
        name = self.maps[index]["name"]
        del self.maps[index]
        if index == self.active_map:
            self.active_map = min(index, len(self.maps) - 1)
            self._load_state(self.maps[self.active_map]["state"])
            self.view.fit_all()
        elif index < self.active_map:
            self.active_map -= 1
        self._refresh_tabs()
        self.statusBar().showMessage(f"Closed map “{name}”.")

    def rename_map(self, index):
        if not (0 <= index < len(self.maps)):
            return
        name, ok = QInputDialog.getText(
            self, "Rename map", "Map name:", text=self.maps[index]["name"])
        if ok and name.strip():
            self.maps[index]["name"] = name.strip()
            self._refresh_tabs()

    # ----- inspector dock
    def _dock_inspector(self, area):
        self.inspector_dock.setFloating(False)
        self.addDockWidget(area, self.inspector_dock)
        self.inspector_dock.show()
        vertical = area in (Qt.LeftDockWidgetArea, Qt.RightDockWidgetArea)
        self.inspector.set_orientation(vertical)
        if vertical:
            self.resizeDocks([self.inspector_dock], [300], Qt.Horizontal)
        else:
            self.resizeDocks([self.inspector_dock], [230], Qt.Vertical)

    def _float_inspector(self):
        self.inspector_dock.setFloating(True)
        self.inspector.set_orientation(True)
        self.inspector_dock.resize(340, 440)
        self.inspector_dock.show()

    def _on_inspector_docked(self, area):
        vertical = area in (Qt.LeftDockWidgetArea, Qt.RightDockWidgetArea)
        self.inspector.set_orientation(vertical)

    def toggle_inspector(self):
        self.inspector_dock.setVisible(not self.inspector_dock.isVisible())

    # ----- search
    def on_search(self, text):
        self._matches = self.scene.apply_search(text)
        self._match_idx = -1
        if text.strip():
            self.statusBar().showMessage(f"{len(self._matches)} match(es) for “{text.strip()}”.")
        else:
            self.statusBar().showMessage("")

    def next_match(self):
        matches = getattr(self, "_matches", [])
        if not matches:
            return
        self._match_idx = (getattr(self, "_match_idx", -1) + 1) % len(matches)
        node = matches[self._match_idx]
        self.scene.clearSelection()
        node.setSelected(True)
        self.view.centerOn(node.connection_point())
        self.view.viewport_changed.emit()
        self.statusBar().showMessage(f"Match {self._match_idx + 1}/{len(matches)}: {node.title}")

    # ----- export
    def export_png(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export as PNG", "mindmap.png",
                                              "PNG image (*.png)")
        if not path:
            return
        if not path.lower().endswith(".png"):
            path += ".png"
        ok = self.scene.render_image(path)
        self.statusBar().showMessage(f"Exported image → {path}" if ok else "PNG export failed.")

    def export_markdown(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export as Markdown", "engagement.md",
                                              "Markdown (*.md)")
        if not path:
            return
        if not path.lower().endswith(".md"):
            path += ".md"
        with open(path, "w") as f:
            f.write(self.scene.to_markdown())
        self.statusBar().showMessage(f"Exported report → {path}")

    def new_map(self):
        self.maps = [{"name": "Map 1", "state": {"nodes": [], "edges": [], "ideas": []}}]
        self.active_map = 0
        self.current_file = None
        self._load_state(self.maps[0]["state"])
        self._refresh_tabs()
        self.view.fit_all()
        self.statusBar().showMessage("New engagement — one empty map.")

    def open_map(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open mind map", "", "MindMapo (*.json)")
        if not path:
            return
        try:
            with open(path) as f:
                data = json.load(f)
            if isinstance(data, dict) and "maps" in data:      # multi-map file
                self.maps = []
                for entry in data["maps"]:
                    self.maps.append({
                        "name": entry.get("name", "Map"),
                        "state": {
                            "nodes": entry.get("nodes", []),
                            "edges": entry.get("edges", []),
                            "ideas": entry.get("ideas", []),
                        },
                    })
                self.active_map = min(int(data.get("active", 0)), len(self.maps) - 1)
            else:                                              # legacy single map
                self.maps = [{
                    "name": "Map 1",
                    "state": {
                        "nodes": data.get("nodes", []),
                        "edges": data.get("edges", []),
                        "ideas": data.get("ideas", []),
                    },
                }]
                self.active_map = 0
            if not self.maps:
                self.maps = [{"name": "Map 1",
                              "state": {"nodes": [], "edges": [], "ideas": []}}]
                self.active_map = 0
            self._load_state(self.maps[self.active_map]["state"])
            self._refresh_tabs()
            self.current_file = path
            self.view.fit_all()
            self.statusBar().showMessage(f"Opened {path} — {len(self.maps)} map(s).")
        except Exception as exc:  # noqa
            self.statusBar().showMessage(f"Failed to open: {exc}")

    def save_map(self):
        path = self.current_file
        if not path:
            path, _ = QFileDialog.getSaveFileName(self, "Save mind map", "engagement.json",
                                                  "MindMapo (*.json)")
            if not path:
                return
            if not path.endswith(".json"):
                path += ".json"
        self._capture_active()
        doc = {"version": 2, "active": self.active_map, "maps": []}
        for m in self.maps:
            entry = dict(m["state"] or {"nodes": [], "edges": [], "ideas": []})
            entry["name"] = m["name"]
            doc["maps"].append(entry)
        with open(path, "w") as f:
            json.dump(doc, f, indent=2)
        self.current_file = path
        self.statusBar().showMessage(f"Saved {path} — {len(self.maps)} map(s).")

    # ------------------------------------------------------------------ glue
    def _sync_inspector(self):
        items = [i for i in self.scene.selectedItems() if isinstance(i, MindNode)]
        self.inspector.set_node(items[0] if len(items) == 1 else None)

    def _on_status(self, msg):
        if msg:
            self.statusBar().showMessage(msg)

    # ------------------------------------------------------------------ sample
    def _make_sample_map(self):
        s = self.scene
        target = s.add_node("target", QPointF(-90, -200), "10.10.10.5  (acme-web01)", animate=False)
        recon = s.add_node("recon", QPointF(-420, -40), "Nmap full TCP", "nmap -p- -sCV", animate=False)
        web = s.add_node("enum", QPointF(-110, 40), "Port 80 — Apache 2.4.49", "path traversal?", animate=False)
        vuln = s.add_node("vuln", QPointF(220, -20), "CVE-2021-41773", "Apache path traversal RCE", animate=False)
        exploit = s.add_node("exploit", QPointF(260, 170), "RCE → www-data", animate=False)
        creds = s.add_node("creds", QPointF(-130, 230), "DB creds in config.php", "root:Sup3rS3cret", animate=False)
        privesc = s.add_node("privesc", QPointF(120, 340), "sudo -l → GTFOBin", animate=False)

        for a, b in [(target, recon), (target, web), (web, vuln), (vuln, exploit),
                     (exploit, creds), (exploit, privesc)]:
            s.connect_nodes(a, b)
        for n in s.nodes:
            n.spawn()

        self.ideas.load([
            {"text": "Test default creds on admin panel", "done": False},
            {"text": "Check for .git / backup files", "done": False},
            {"text": "Fuzz the file-upload endpoint", "done": True},
        ])


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("MindMapo")
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(style_sheet())
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
