"""A small overview navigator that floats over the canvas.

Shows every (visible) node as a colored dot plus the current viewport, and lets
you click / drag anywhere on it to jump the main view there.
"""

from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QPainterPath
from PySide6.QtWidgets import QWidget

from categories import get_category, THEME


class Minimap(QWidget):
    def __init__(self, view):
        super().__init__(view)
        self.view = view
        self.setFixedSize(230, 165)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        view.viewport_changed.connect(self._on_change)

    # ------------------------------------------------------------------ helpers
    def _on_change(self):
        self.reposition()
        self.update()

    def reposition(self):
        p = self.parentWidget()
        if p:
            self.move(p.width() - self.width() - 22, p.height() - self.height() - 22)
            self.raise_()

    def _content_rect(self):
        scene = self.view.scene()
        rect = scene.content_rect()
        if rect.isNull():
            rect = self.view.mapToScene(self.view.viewport().rect()).boundingRect()
        return rect.adjusted(-120, -120, 120, 120)

    def _params(self):
        """Return (content_rect, scale, ox, oy) mapping scene→widget."""
        inner = self.rect().adjusted(10, 10, -10, -10)
        content = self._content_rect()
        cw = max(content.width(), 1.0)
        ch = max(content.height(), 1.0)
        scale = min(inner.width() / cw, inner.height() / ch)
        ox = inner.x() + (inner.width() - cw * scale) / 2 - content.x() * scale
        oy = inner.y() + (inner.height() - ch * scale) / 2 - content.y() * scale
        return content, scale, ox, oy

    def _scene_to_widget(self, pt, scale, ox, oy):
        return QPointF(pt.x() * scale + ox, pt.y() * scale + oy)

    def _widget_to_scene(self, pt, scale, ox, oy):
        return QPointF((pt.x() - ox) / scale, (pt.y() - oy) / scale)

    # ------------------------------------------------------------------ paint
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        panel = QPainterPath()
        panel.addRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 14, 14)
        p.fillPath(panel, QColor(14, 19, 38, 235))
        p.setPen(QPen(QColor(THEME["border"]), 1.2))
        p.drawPath(panel)

        scene = self.view.scene()
        if not scene.nodes:
            p.setPen(QColor(THEME["text_dim"]))
            p.drawText(self.rect(), Qt.AlignCenter, "overview")
            return

        content, scale, ox, oy = self._params()

        # Nodes as dots.
        p.setPen(Qt.NoPen)
        for n in scene.nodes:
            if not n.isVisible():
                continue
            c = self._scene_to_widget(n.connection_point(), scale, ox, oy)
            color = QColor(get_category(n.category).color)
            if n.dimmed:
                color.setAlpha(60)
            p.setBrush(color)
            p.drawEllipse(c, 2.6, 2.6)

        # Current viewport rectangle.
        vp = self.view.mapToScene(self.view.viewport().rect()).boundingRect()
        tl = self._scene_to_widget(vp.topLeft(), scale, ox, oy)
        br = self._scene_to_widget(vp.bottomRight(), scale, ox, oy)
        vr = QRectF(tl, br).intersected(QRectF(self.rect()).adjusted(2, 2, -2, -2))
        p.setBrush(QColor(255, 204, 0, 28))
        p.setPen(QPen(QColor("#FFCC00"), 1.4))
        p.drawRoundedRect(vr, 4, 4)

    # ------------------------------------------------------------------ navigate
    def _jump(self, widget_pt):
        _, scale, ox, oy = self._params()
        target = self._widget_to_scene(QPointF(widget_pt), scale, ox, oy)
        self.view.centerOn(target)
        self.view.viewport_changed.emit()

    def mousePressEvent(self, e):
        self._jump(e.position())

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.LeftButton:
            self._jump(e.position())
