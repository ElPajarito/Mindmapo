"""Animated mind-map node.

A node is a glossy rounded "block" with a neon glow. It bounces in when spawned,
gently floats while idle, and pops on hover — giving the canvas a lively,
arcade-world feel.
"""

from PySide6.QtCore import (
    Qt, QPointF, QRectF, QPropertyAnimation, QEasingCurve, Property, Signal,
)
from PySide6.QtGui import (
    QColor, QPen, QBrush, QFont, QPainterPath, QLinearGradient, QFontMetrics,
)
from PySide6.QtWidgets import (
    QGraphicsObject, QGraphicsDropShadowEffect, QStyle,
)

from categories import get_category, THEME


MARGIN = 22          # painting headroom for glow / pop scale
BLOCK_H = 62
MIN_W = 150
MAX_W = 300


class MindNode(QGraphicsObject):
    """One piece of intel on the board."""

    def __init__(self, node_id, category="note", title="New node", notes="", pos=QPointF(0, 0)):
        super().__init__()
        self.node_id = node_id
        self.category = category
        self._title = title
        self.notes = notes
        self.edges = []

        self._w = MIN_W
        self._float = 0.0
        self._base = QPointF(pos)
        self._internal_move = False
        self._dragging = False
        self._hover = False
        self.collapsed = False          # subtree folded into this node?
        self.hidden_count = 0           # descendants currently hidden under it
        self.dimmed = False             # filtered-out (search) -> faded

        self.setFlags(
            QGraphicsObject.ItemIsMovable
            | QGraphicsObject.ItemIsSelectable
            | QGraphicsObject.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self.setPos(self._base)
        self._recalc_width()

        # Neon glow that matches the category color.
        self._glow = QGraphicsDropShadowEffect()
        self._glow.setBlurRadius(34)
        self._glow.setOffset(0, 6)
        self._refresh_glow()
        self.setGraphicsEffect(self._glow)

        # Animations -------------------------------------------------------
        self._pop = QPropertyAnimation(self, b"scale", self)
        self._float_anim = QPropertyAnimation(self, b"floatOffset", self)
        self._float_anim.setDuration(2600)
        self._float_anim.setLoopCount(-1)
        self._float_anim.setKeyValueAt(0.0, 0.0)
        self._float_anim.setKeyValueAt(0.5, -7.0)
        self._float_anim.setKeyValueAt(1.0, 0.0)
        self._float_anim.setEasingCurve(QEasingCurve.InOutSine)

    # ------------------------------------------------------------------ props
    def _get_float(self):
        return self._float

    def _set_float(self, v):
        self._float = v
        self._internal_move = True
        self.setPos(self._base.x(), self._base.y() + v)
        self._internal_move = False
        for e in self.edges:
            e.adjust()

    floatOffset = Property(float, _get_float, _set_float)

    @property
    def title(self):
        return self._title

    def set_title(self, text):
        self.prepareGeometryChange()
        self._title = text or ""
        self._recalc_width()
        self.update()
        for e in self.edges:
            e.adjust()

    def set_category(self, key):
        self.category = key
        self._refresh_glow()
        self.update()
        for e in self.edges:
            e.adjust()

    # ------------------------------------------------------------------ geom
    def _recalc_width(self):
        fm = QFontMetrics(QFont("Segoe UI", 11, QFont.Bold))
        tw = fm.horizontalAdvance(self._title) + 70
        self._w = max(MIN_W, min(MAX_W, tw))
        self.setTransformOriginPoint(self._w / 2, BLOCK_H / 2)

    def boundingRect(self):
        return QRectF(-MARGIN, -MARGIN, self._w + 2 * MARGIN, BLOCK_H + 2 * MARGIN)

    def block_rect(self):
        return QRectF(0, 0, self._w, BLOCK_H)

    def shape(self):
        path = QPainterPath()
        path.addRoundedRect(self.block_rect(), 16, 16)
        return path

    def connection_point(self):
        return self.mapToScene(QPointF(self._w / 2, BLOCK_H / 2))

    # ------------------------------------------------------------------ glow
    def _refresh_glow(self):
        c = QColor(get_category(self.category).color)
        c.setAlpha(170)
        self._glow.setColor(c)

    def set_glow_enabled(self, on):
        self._glow.setEnabled(on)

    def pause_float(self):
        if self._float_anim.state() == QPropertyAnimation.Running:
            self._float_anim.pause()

    def resume_float(self):
        if self._float_anim.state() == QPropertyAnimation.Paused:
            self._float_anim.resume()

    def _lod_simple(self):
        sc = self.scene()
        return bool(getattr(sc, "simple_lod", False))

    # ------------------------------------------------------------------ paint
    def paint(self, p, option, widget=None):
        p.setRenderHint(p.RenderHint.Antialiasing, True)
        cat = get_category(self.category)
        base = QColor(cat.color)
        rect = self.block_rect()

        if self.dimmed:
            p.setOpacity(0.18)

        selected = bool(option.state & QStyle.State_Selected)

        # Glossy vertical gradient.
        grad = QLinearGradient(0, 0, 0, BLOCK_H)
        grad.setColorAt(0.0, base.lighter(135))
        grad.setColorAt(0.5, base)
        grad.setColorAt(1.0, base.darker(135))

        path = QPainterPath()
        path.addRoundedRect(rect, 16, 16)
        p.fillPath(path, QBrush(grad))

        # Border — white pop when selected, soft highlight otherwise.
        if selected:
            p.setPen(QPen(QColor("#ffffff"), 3))
        else:
            p.setPen(QPen(base.lighter(160), 1.5))
        p.drawPath(path)

        # Level-of-detail: when zoomed far out, skip the costly fine detail
        # (shine, pill text, title halo) and just show a labelled color block.
        if self._lod_simple():
            p.setFont(QFont("Segoe UI Emoji", 18))
            p.setPen(QColor("#ffffff"))
            p.drawText(rect, Qt.AlignCenter, cat.emoji)
            if self.collapsed and self.hidden_count:
                self._draw_collapse_badge(p)
            return

        # Top "shine" strip for a candy/3D look.
        shine = QPainterPath()
        shine.addRoundedRect(QRectF(6, 5, self._w - 12, BLOCK_H * 0.42), 12, 12)
        sc = QColor(255, 255, 255, 46)
        p.fillPath(shine, sc)

        # Category pill (top-left).
        pill = QRectF(12, 9, 0, 18)
        fm_small = QFontMetrics(QFont("Segoe UI", 7, QFont.Bold))
        label = cat.label.upper()
        pill.setWidth(fm_small.horizontalAdvance(label) + 18)
        pill_path = QPainterPath()
        pill_path.addRoundedRect(pill, 9, 9)
        p.fillPath(pill_path, QColor(0, 0, 0, 115))
        p.setPen(QColor(255, 255, 255, 245))
        p.setFont(QFont("Segoe UI", 7, QFont.Bold))
        p.drawText(pill.adjusted(9, 0, 0, 0), Qt.AlignVCenter | Qt.AlignLeft, label)

        # Emoji badge.
        p.setFont(QFont("Segoe UI Emoji", 16))
        p.setPen(QColor("#ffffff"))
        p.drawText(QRectF(10, 26, 34, 30), Qt.AlignCenter, cat.emoji)

        # Title — white text with a dark halo so it stays legible on ANY
        # category color (gold, teal, orange…) and over the busy glow/edges.
        p.setFont(QFont("Segoe UI", 11, QFont.Bold))
        trect = QRectF(46, 26, self._w - 56, 30)
        fm = QFontMetrics(p.font())
        elided = fm.elidedText(self._title, Qt.ElideRight, int(trect.width()))
        self._draw_outlined_text(p, trect, Qt.AlignVCenter | Qt.AlignLeft, elided)

        if self.collapsed and self.hidden_count:
            self._draw_collapse_badge(p)

    def _draw_collapse_badge(self, p):
        """A '+N' bubble on the bottom-right showing hidden descendants."""
        text = f"+{self.hidden_count}"
        fm = QFontMetrics(QFont("Segoe UI", 9, QFont.Bold))
        w = max(22, fm.horizontalAdvance(text) + 12)
        rect = QRectF(self._w - w + 6, BLOCK_H - 12, w, 22)
        path = QPainterPath()
        path.addRoundedRect(rect, 11, 11)
        p.fillPath(path, QColor("#0e1326"))
        p.setPen(QPen(QColor("#FFCC00"), 1.5))
        p.drawPath(path)
        p.setPen(QColor("#FFCC00"))
        p.setFont(QFont("Segoe UI", 9, QFont.Bold))
        p.drawText(rect, Qt.AlignCenter, text)

    def _draw_outlined_text(self, p, rect, flags, text,
                            fill=QColor("#ffffff"), outline=QColor(6, 10, 20, 235)):
        """Draw text with a thin contrasting outline for maximum legibility."""
        p.setPen(outline)
        for dx, dy in ((-1.2, 0), (1.2, 0), (0, -1.2), (0, 1.2),
                       (-1, -1), (1, -1), (-1, 1), (1, 1)):
            p.drawText(rect.translated(dx, dy), flags, text)
        p.setPen(fill)
        p.drawText(rect, flags, text)

    # ------------------------------------------------------------------ anim
    def spawn(self):
        """Bouncy entrance."""
        self.setScale(0.1)
        self._pop.stop()
        self._pop.setDuration(560)
        self._pop.setStartValue(0.1)
        self._pop.setEndValue(1.0)
        self._pop.setEasingCurve(QEasingCurve.OutBack)
        self._pop.start()
        self._float_anim.start()

    def _pop_to(self, value, dur=140, curve=QEasingCurve.OutBack):
        self._pop.stop()
        self._pop.setDuration(dur)
        self._pop.setStartValue(self.scale())
        self._pop.setEndValue(value)
        self._pop.setEasingCurve(curve)
        self._pop.start()

    # ------------------------------------------------------------------ events
    def hoverEnterEvent(self, e):
        self._hover = True
        self.setZValue(10)
        self._pop_to(1.08)
        self.setCursor(Qt.OpenHandCursor)
        super().hoverEnterEvent(e)

    def hoverLeaveEvent(self, e):
        self._hover = False
        self.setZValue(1 if not self.isSelected() else 5)
        self._pop_to(1.0, dur=180, curve=QEasingCurve.OutCubic)
        super().hoverLeaveEvent(e)

    def mousePressEvent(self, e):
        self._dragging = True
        self._float_anim.pause()
        self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        self._dragging = False
        # Re-anchor float baseline to wherever we dropped it.
        self._base = QPointF(self.pos().x(), self.pos().y() - self._float)
        self._float_anim.resume()
        self.setCursor(Qt.OpenHandCursor)
        self._pop_to(1.0, dur=160, curve=QEasingCurve.OutCubic)
        super().mouseReleaseEvent(e)

    def mouseDoubleClickEvent(self, e):
        scene = self.scene()
        if scene is not None:
            scene.request_rename(self)
        super().mouseDoubleClickEvent(e)

    def itemChange(self, change, value):
        if change == QGraphicsObject.ItemPositionChange and not self._internal_move:
            # User drag: keep the float baseline in sync with the new position.
            self._base = QPointF(value.x(), value.y() - self._float)
        elif change == QGraphicsObject.ItemPositionHasChanged:
            for e in self.edges:
                e.adjust()
        elif change == QGraphicsObject.ItemSelectedHasChanged:
            self.setZValue(5 if value else 1)
        return super().itemChange(change, value)

    def contextMenuEvent(self, e):
        scene = self.scene()
        if scene is not None:
            scene.show_node_menu(self, e.screenPos())
        e.accept()

    # ------------------------------------------------------------------ data
    def to_dict(self):
        return {
            "id": self.node_id,
            "category": self.category,
            "title": self._title,
            "notes": self.notes,
            "x": self._base.x(),
            "y": self._base.y(),
        }
