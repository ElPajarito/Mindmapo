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
    QTextDocument,
)
from PySide6.QtWidgets import (
    QGraphicsObject, QStyle, QGraphicsItem,
)

from categories import get_category, THEME


def _looks_like_html(s):
    s = (s or "").lower()
    return any(t in s for t in ("</", "<p", "<span", "<br", "<html", "<ul", "<ol", "<li"))


MARGIN = 26          # painting headroom for glow / pop scale
BLOCK_H = 62
MIN_W = 150
MAX_W = 300
DRAG_THRESHOLD = 4   # scene units a press must travel before it counts as a drag


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
        self._drag_active = False        # crossed the threshold -> fast render mode
        self._press_pos = QPointF(0, 0)
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

        # Cache the rendered node (glow included) as a device-space pixmap: while
        # it merely moves (float / drag / pan) the cached bitmap is re-blitted
        # instead of re-painting the glow every frame — the key to cheap frames
        # at a high refresh rate. It re-renders only on zoom / edit.
        self.setCacheMode(QGraphicsItem.DeviceCoordinateCache)

        # Neon glow. It is painted by hand in paint() (a soft category-colored
        # halo) rather than via QGraphicsDropShadowEffect: that effect crashes
        # inside Qt's paint traversal (QGraphicsItemPrivate::effectiveBoundingRect)
        # on this Qt/driver combo when the scene is mutated live — e.g. adding a
        # node or clearing a filled map to open a new tab. Hand-painting is
        # stable and, thanks to the device cache above, just as cheap.
        self._glow_on = True

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
        # Glow color is read from the category at paint time; just repaint.
        self.update()

    def set_glow_enabled(self, on):
        if on != self._glow_on:
            self._glow_on = on
            self.update()

    def pause_float(self):
        if self._float_anim.state() == QPropertyAnimation.Running:
            self._float_anim.pause()

    def resume_float(self):
        if self._float_anim.state() == QPropertyAnimation.Paused:
            self._float_anim.resume()

    def teardown(self):
        """Release timers / device cache before the node leaves the scene.

        Stops the never-ending float animation so nothing repaints the item
        after removal, and drops the DeviceCoordinateCache pixmap (bound to the
        viewport) so it isn't freed later against a live GL context.
        """
        for anim in (self._pop, self._float_anim):
            anim.stop()
        self.setCacheMode(QGraphicsItem.NoCache)

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

        # Neon glow — a soft category-colored halo painted as a few expanding,
        # fading rounded outlines just below the block (replaces the crash-prone
        # QGraphicsDropShadowEffect). Skipped while dimmed or at low LOD.
        if self._glow_on and not self.dimmed and not self._lod_simple():
            self._paint_glow(p, base)

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
        # The point size scales with the *view* zoom: as you zoom out the font
        # grows (never below the base size) so titles stay readable, capped so
        # they still fit the block; zoomed in it settles back to the base size.
        zoom = getattr(self.scene(), "view_scale", 1.0) or 1.0
        pt = 14.0 / (1.333 * max(zoom, 0.05))
        pt = max(11.0, min(pt, 20.0))
        title_font = QFont("Segoe UI")
        title_font.setBold(True)
        title_font.setPointSizeF(pt)
        p.setFont(title_font)
        fm = QFontMetrics(title_font)
        th = fm.height()
        trect = QRectF(46, 41 - th / 2, self._w - 56, th)
        elided = fm.elidedText(self._title, Qt.ElideRight, int(trect.width()))
        self._draw_outlined_text(p, trect, Qt.AlignVCenter | Qt.AlignLeft, elided)

        if self.collapsed and self.hidden_count:
            self._draw_collapse_badge(p)

    def _paint_glow(self, p, base):
        """Soft neon halo: concentric fading rounded fills around the block,
        nudged down a touch to read like a light source from above."""
        p.setPen(Qt.NoPen)
        rect = self.block_rect().translated(0, 5)
        layers = 6
        for i in range(layers, 0, -1):
            grow = i * 3.0                       # outermost ring ~18px out (< MARGIN)
            col = QColor(base)
            col.setAlpha(int(10 + 42 * (1 - (i - 1) / (layers - 1))))
            halo = QPainterPath()
            halo.addRoundedRect(rect.adjusted(-grow, -grow, grow, grow),
                                16 + grow * 0.5, 16 + grow * 0.5)
            p.fillPath(halo, col)

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
        self._drag_active = False
        self._press_pos = e.scenePos()
        self.pause_float()
        self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        # Only once the pointer has actually travelled do we treat this as a
        # drag and shed the costly glow/animations — a plain click never blinks.
        if self._dragging and not self._drag_active:
            if (e.scenePos() - self._press_pos).manhattanLength() > DRAG_THRESHOLD:
                self._drag_active = True
                sc = self.scene()
                if sc is not None:
                    sc.set_interaction_fast(True)
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        self._dragging = False
        # Re-anchor float baseline to wherever we dropped it.
        self._base = QPointF(self.pos().x(), self.pos().y() - self._float)
        if self._drag_active:
            self._drag_active = False
            sc = self.scene()
            if sc is not None:
                sc.set_interaction_fast(False)      # restores glow + floats (incl. this node)
        else:
            self.resume_float()                     # plain click: undo the press-time pause
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
    def plain_notes(self):
        """Notes as plain text (notes may be stored as rich-text HTML)."""
        src = self.notes or ""
        if getattr(self, "_pn_src", None) == src:
            return self._pn_cache
        if _looks_like_html(src):
            doc = QTextDocument()
            doc.setHtml(src)
            txt = doc.toPlainText()
        else:
            txt = src
        self._pn_src, self._pn_cache = src, txt
        return txt

    def to_dict(self):
        return {
            "id": self.node_id,
            "category": self.category,
            "title": self._title,
            "notes": self.notes,
            "x": self._base.x(),
            "y": self._base.y(),
        }
