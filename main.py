#!/usr/bin/env python3
"""MindMapo — a lively, interactive mind map for pentest engagements.

Run:  python3 main.py
"""

import json
import sys

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QAction, QKeySequence, QFont, QColor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QComboBox, QLineEdit, QPlainTextEdit,
    QFileDialog, QToolBar, QSizePolicy, QGraphicsView, QMenu, QToolButton,
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
    """Right panel: edit the selected node's title / category / notes."""

    def __init__(self, scene, parent=None):
        super().__init__(parent)
        self.setObjectName("Inspector")
        self.scene = scene
        self.node = None
        self.setFixedWidth(280)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(8)

        lay.addWidget(self._label("INSPECTOR", "SectionLabel"))
        self.title_lbl = QLabel("No node selected")
        self.title_lbl.setObjectName("PanelTitle")
        self.title_lbl.setWordWrap(True)
        lay.addWidget(self.title_lbl)

        lay.addWidget(self._label("TITLE", "SectionLabel"))
        self.title_edit = QLineEdit()
        self.title_edit.textEdited.connect(self._on_title)
        lay.addWidget(self.title_edit)

        lay.addWidget(self._label("CATEGORY", "SectionLabel"))
        self.cat_combo = QComboBox()
        for key, cat in CATEGORIES.items():
            self.cat_combo.addItem(f"{cat.emoji}  {cat.label}", key)
        self.cat_combo.currentIndexChanged.connect(self._on_category)
        lay.addWidget(self.cat_combo)

        lay.addWidget(self._label("INTEL / NOTES", "SectionLabel"))
        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setPlaceholderText("Creds, ports, payloads, observations…")
        self.notes_edit.textChanged.connect(self._on_notes)
        lay.addWidget(self.notes_edit, 1)

        self.del_btn = QPushButton("\U0001F5D1  Delete node")
        self.del_btn.setObjectName("danger")
        self.del_btn.clicked.connect(self._delete)
        lay.addWidget(self.del_btn)

        self._busy = False
        self.set_node(None)

    def _label(self, text, obj):
        l = QLabel(text)
        l.setObjectName(obj)
        return l

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

    def __init__(self, on_add, parent=None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(220)
        self.on_add = on_add

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 16, 14, 16)
        outer.setSpacing(6)

        outer.addWidget(self._section("ADD A NODE"))

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
        outer.addWidget(scroll, 1)

        hint = QLabel("Tip: right-click a node to add a child.\nDrag to move • Wheel to zoom • Alt-drag to pan")
        hint.setObjectName("SectionLabel")
        hint.setWordWrap(True)
        outer.addWidget(hint)

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
        self.inspector = Inspector(self.scene)

        central = QWidget()
        h = QHBoxLayout(central)
        h.setContentsMargins(12, 12, 12, 12)
        h.setSpacing(12)
        h.addWidget(self.sidebar)
        h.addWidget(self.view, 1)
        h.addWidget(self.inspector)
        self.setCentralWidget(central)

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
        self.scene.clear_map()
        self.current_file = None
        self.inspector.set_node(None)
        self.ideas.load([])
        self.statusBar().showMessage("New empty map.")

    def open_map(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open mind map", "", "MindMapo (*.json)")
        if not path:
            return
        try:
            with open(path) as f:
                data = json.load(f)
            self.scene.from_dict(data)
            self.ideas.load(data.get("ideas", []))
            self.current_file = path
            self.view.fit_all()
            self.statusBar().showMessage(f"Opened {path}")
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
        data = self.scene.to_dict()
        data["ideas"] = self.ideas.to_list()
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        self.current_file = path
        self.statusBar().showMessage(f"Saved {path}")

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
