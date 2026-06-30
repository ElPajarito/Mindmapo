"""A discreet, collapsible brainstorm pad that floats over the canvas.

Jot quick ideas to throw at an asset, tick them off as you try them. It stays
faded and out of the way until you hover it, collapses to a small pill, and is
saved/loaded alongside the rest of the map.
"""

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
    QCheckBox, QScrollArea, QToolButton, QGraphicsOpacityEffect, QLabel,
)


class IdeaTracker(QFrame):
    def __init__(self, view):
        super().__init__(view)
        self.view = view
        self.ideas = []            # list of {"text": str, "done": bool}
        self.expanded = False
        self.setObjectName("IdeaPanel")
        self.setFixedWidth(258)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(8)

        self.header = QPushButton()
        self.header.setObjectName("IdeaHeader")
        self.header.setCursor(Qt.PointingHandCursor)
        self.header.clicked.connect(self.toggle)
        outer.addWidget(self.header)

        # --- body (hidden when collapsed) ---
        self.body = QWidget()
        body_lay = QVBoxLayout(self.body)
        body_lay.setContentsMargins(0, 0, 0, 0)
        body_lay.setSpacing(8)

        self.add_edit = QLineEdit()
        self.add_edit.setObjectName("IdeaAdd")
        self.add_edit.setPlaceholderText("New idea for this asset…  ↵")
        self.add_edit.returnPressed.connect(self._add_from_edit)
        body_lay.addWidget(self.add_edit)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("IdeaScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.holder = QWidget()
        self.list_lay = QVBoxLayout(self.holder)
        self.list_lay.setContentsMargins(0, 0, 4, 0)
        self.list_lay.setSpacing(4)
        self.list_lay.addStretch(1)
        self.scroll.setWidget(self.holder)
        body_lay.addWidget(self.scroll)

        self.empty = QLabel("No ideas yet — type one above.")
        self.empty.setObjectName("IdeaEmpty")
        self.empty.setAlignment(Qt.AlignCenter)
        body_lay.addWidget(self.empty)

        outer.addWidget(self.body)

        # Faded by default; brighten on hover so it's discreet but reachable.
        self._fx = QGraphicsOpacityEffect(self)
        self._fx.setOpacity(0.72)
        self.setGraphicsEffect(self._fx)

        view.viewport_changed.connect(self.reposition)
        self._rebuild()
        self._apply_state()

    # ------------------------------------------------------------------ hover fade
    def enterEvent(self, e):
        self._fx.setOpacity(1.0)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._fx.setOpacity(0.72)
        super().leaveEvent(e)

    # ------------------------------------------------------------------ placement
    def reposition(self):
        p = self.parentWidget()
        if p:
            self.move(p.width() - self.width() - 22, 16)
            self.raise_()

    def _apply_state(self):
        self.body.setVisible(self.expanded)
        self._update_header()
        self.resize(self.width(), self.sizeHint().height())
        self.reposition()

    def toggle(self):
        self.expanded = not self.expanded
        self._apply_state()

    def _update_header(self):
        total = len(self.ideas)
        done = sum(1 for i in self.ideas if i["done"])
        arrow = "▾" if self.expanded else "▸"
        self.header.setText(f"{arrow}   \U0001F4A1  Ideas   ·   {done}/{total}")

    # ------------------------------------------------------------------ data
    def to_list(self):
        return [dict(i) for i in self.ideas]

    def load(self, items):
        self.ideas = [{"text": str(i.get("text", "")), "done": bool(i.get("done", False))}
                      for i in (items or []) if i.get("text")]
        self._rebuild()
        self._apply_state()

    def _add_from_edit(self):
        text = self.add_edit.text().strip()
        if not text:
            return
        self.ideas.append({"text": text, "done": False})
        self.add_edit.clear()
        self._rebuild()
        if not self.expanded:
            self.expanded = True
        self._apply_state()

    def _delete(self, idea):
        if idea in self.ideas:
            self.ideas.remove(idea)
        self._rebuild()
        self._apply_state()

    def _toggle_done(self, idea, cb):
        idea["done"] = cb.isChecked()
        self._style_check(cb, idea["done"])
        self._update_header()

    # ------------------------------------------------------------------ rows
    def _style_check(self, cb, done):
        f = QFont("Segoe UI", 10)
        f.setStrikeOut(done)
        cb.setFont(f)
        cb.setStyleSheet("color:#6b779c;" if done else "color:#e8edf7;")

    def _clear_rows(self):
        while self.list_lay.count() > 1:           # keep trailing stretch
            item = self.list_lay.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _rebuild(self):
        self._clear_rows()
        for idea in self.ideas:
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(2, 0, 0, 0)
            rl.setSpacing(4)
            cb = QCheckBox(idea["text"])
            cb.setToolTip(idea["text"])
            cb.setChecked(idea["done"])
            self._style_check(cb, idea["done"])
            cb.toggled.connect(lambda _=False, i=idea, c=cb: self._toggle_done(i, c))
            rl.addWidget(cb, 1)
            x = QToolButton()
            x.setObjectName("IdeaDel")
            x.setText("✕")
            x.setCursor(Qt.PointingHandCursor)
            x.setToolTip("Remove idea")
            x.clicked.connect(lambda _=False, i=idea: self._delete(i))
            rl.addWidget(x, 0)
            self.list_lay.insertWidget(self.list_lay.count() - 1, row)

        has = bool(self.ideas)
        self.scroll.setVisible(has)
        self.empty.setVisible(not has)
        if has:
            wanted = self.holder.sizeHint().height()
            self.scroll.setFixedHeight(min(max(wanted, 30), 230))
        self._update_header()

    def sizeHint(self):
        return QSize(self.width(), super().sizeHint().height())
