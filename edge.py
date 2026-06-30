"""Curved, color-blended connection between two nodes with a flowing pulse."""

from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QColor, QPen, QPainterPath, QPainterPathStroker, QLinearGradient
from PySide6.QtWidgets import QGraphicsObject

from categories import get_category


class Edge(QGraphicsObject):
    def __init__(self, source, dest):
        super().__init__()
        self.source = source
        self.dest = dest
        self._p1 = QPointF()
        self._p2 = QPointF()
        self._c1 = QPointF()
        self._c2 = QPointF()
        self._phase = 0.0
        self._hover = False
        self.setZValue(-1)
        self.setFlag(QGraphicsObject.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)
        source.edges.append(self)
        dest.edges.append(self)
        self.adjust()

    def other(self, node):
        return self.dest if node is self.source else self.source

    def set_phase(self, phase):
        self._phase = phase
        self.update()

    def adjust(self):
        self.prepareGeometryChange()
        self._p1 = self.source.connection_point()
        self._p2 = self.dest.connection_point()
        dx = (self._p2.x() - self._p1.x()) * 0.5
        # Horizontal-biased control points -> smooth S-curve.
        self._c1 = QPointF(self._p1.x() + dx, self._p1.y())
        self._c2 = QPointF(self._p2.x() - dx, self._p2.y())
        self.update()

    def _path(self):
        path = QPainterPath(self._p1)
        path.cubicTo(self._c1, self._c2, self._p2)
        return path

    def boundingRect(self):
        return self._path().boundingRect().adjusted(-10, -10, 10, 10)

    def shape(self):
        # Widen the thin curve so it is comfortably clickable / selectable.
        stroker = QPainterPathStroker()
        stroker.setWidth(16)
        return stroker.createStroke(self._path())

    def paint(self, p, option, widget=None):
        p.setRenderHint(p.RenderHint.Antialiasing, True)
        path = self._path()

        if self.source.dimmed or self.dest.dimmed:
            p.setOpacity(0.12)

        simple = bool(getattr(self.scene(), "simple_lod", False))

        c1 = QColor(get_category(self.source.category).color)
        c2 = QColor(get_category(self.dest.category).color)

        grad = QLinearGradient(self._p1, self._p2)
        grad.setColorAt(0.0, c1)
        grad.setColorAt(1.0, c2)

        # Highlight when selected or hovered so it's clear which link is targeted.
        if self.isSelected() or self._hover:
            hl = QColor("#ffffff") if self.isSelected() else QColor(255, 255, 255, 120)
            p.setPen(QPen(hl, 7 if self.isSelected() else 6, Qt.SolidLine, Qt.RoundCap))
            p.drawPath(path)

        # Soft outer glow.
        glow = QColor(c1)
        glow.setAlpha(60)
        p.setPen(QPen(glow, 9, Qt.SolidLine, Qt.RoundCap))
        p.drawPath(path)

        # Core line.
        pen = QPen(grad, 3, Qt.SolidLine, Qt.RoundCap)
        p.setPen(pen)
        p.drawPath(path)

        # Flowing dashed overlay (the "energy" running between nodes).
        # Skipped at low LOD — that animation is the main per-frame cost.
        if not simple:
            flow = QPen(QColor(255, 255, 255, 150), 2, Qt.CustomDashLine, Qt.RoundCap)
            flow.setDashPattern([2, 8])
            flow.setDashOffset(-self._phase)
            p.setPen(flow)
            p.drawPath(path)

    def hoverEnterEvent(self, e):
        self._hover = True
        self.setCursor(Qt.PointingHandCursor)
        self.update()
        super().hoverEnterEvent(e)

    def hoverLeaveEvent(self, e):
        self._hover = False
        self.update()
        super().hoverLeaveEvent(e)

    def contextMenuEvent(self, e):
        scene = self.scene()
        if scene is not None:
            scene.show_edge_menu(self, e.screenPos())
        e.accept()

    def to_dict(self):
        return {"a": self.source.node_id, "b": self.dest.node_id}
