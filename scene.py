"""The interactive canvas: scene (model + behaviour) and view (zoom/pan/render)."""

import math
import random

from PySide6.QtCore import Qt, QPointF, QRectF, QTimer, Signal
from PySide6.QtGui import (
    QColor, QPainter, QBrush, QLinearGradient, QFont, QImage, QGuiApplication,
)
from PySide6.QtWidgets import (
    QGraphicsScene, QGraphicsView, QMenu, QInputDialog, QGraphicsItem,
)

from categories import CATEGORIES, get_category, THEME
from node import MindNode
from edge import Edge


# Above these node counts we shed expensive effects to stay smooth.
PERF_GLOW_LIMIT = 90
PERF_FLOAT_LIMIT = 160


class MindScene(QGraphicsScene):
    selection_info_changed = Signal()
    status_message = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(-4000, -4000, 8000, 8000)
        self.nodes = []
        self.edges = []
        self._id_counter = 0
        self.link_mode = False
        self._link_source = None
        self.simple_lod = False        # zoomed-out / low-detail rendering
        self._fast = False             # active pan/drag: shed expensive effects
        self.view_scale = 1.0          # current view zoom (drives node text sizing)
        self.search_query = ""
        self.lane_bands = []           # swimlane backgrounds (label, color, y0, y1)

        # Animated background dots.
        random.seed(7)
        self._stars = [
            (random.uniform(-4000, 4000), random.uniform(-4000, 4000),
             random.uniform(0.6, 2.2), random.uniform(0.2, 1.0))
            for _ in range(220)
        ]

        # Drive the flowing-edge animation + subtle background drift at the
        # display's refresh rate (so it's as smooth as the monitor allows),
        # while keeping the motion *speed* constant regardless of that rate.
        self._phase = 0.0
        hz = 60.0
        screen = QGuiApplication.primaryScreen()
        if screen is not None and screen.refreshRate() > 1:
            hz = screen.refreshRate()
        self._tick_ms = max(6, int(round(1000.0 / hz)))     # e.g. 144 Hz -> 7 ms
        self._phase_step = self._tick_ms / 40.0             # 40 ms tick == 1.0 (original speed)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(self._tick_ms)

    # ------------------------------------------------------------------ tick
    def _tick(self):
        # At low LOD (or while actively panning/dragging) the flowing-edge +
        # background drift animations are paused; the single biggest per-frame
        # saving on a busy board.
        if self.simple_lod or self._fast:
            return
        self._phase += self._phase_step
        for e in self.edges:
            if e.isVisible():
                e.set_phase(self._phase)
        self.invalidate(self.sceneRect(), QGraphicsScene.BackgroundLayer)

    # ------------------------------------------------------------------ model
    def _next_id(self):
        self._id_counter += 1
        return self._id_counter

    def add_node(self, category, pos, title=None, notes="", animate=True, node_id=None):
        if node_id is None:
            node_id = self._next_id()
        else:
            self._id_counter = max(self._id_counter, node_id)
        if title is None:
            title = get_category(category).label
        node = MindNode(node_id, category, title, notes, QPointF(pos))
        self.addItem(node)
        self.nodes.append(node)
        if animate:
            node.spawn()
        self.update_performance_mode()
        return node

    def add_child(self, parent):
        cp = parent.connection_point()
        angle = random.uniform(-0.6, 0.6)
        offset = QPointF(220 * math.cos(angle), 150 * math.sin(angle) + 90)
        pos = cp + offset - QPointF(75, 31)
        child = self.add_node(parent.category, pos, title="New node")
        self.connect_nodes(parent, child)
        self.clearSelection()
        child.setSelected(True)
        self.selection_info_changed.emit()
        return child

    def connect_nodes(self, a, b):
        if a is b:
            return None
        for e in self.edges:
            if {e.source, e.dest} == {a, b}:
                return e
        edge = Edge(a, b)
        self.addItem(edge)
        self.edges.append(edge)
        return edge

    def delete_node(self, node):
        for e in list(node.edges):
            self.remove_edge(e)
        if node in self.nodes:
            self.nodes.remove(node)
        self.removeItem(node)
        self.refresh_visibility()
        self.update_performance_mode()
        self.selection_info_changed.emit()

    def remove_edge(self, edge):
        if edge in edge.source.edges:
            edge.source.edges.remove(edge)
        if edge in edge.dest.edges:
            edge.dest.edges.remove(edge)
        if edge in self.edges:
            self.edges.remove(edge)
        self.removeItem(edge)

    def delete_selected(self):
        for item in list(self.selectedItems()):
            if isinstance(item, MindNode):
                self.delete_node(item)
            elif isinstance(item, Edge):
                self.remove_edge(item)
                self.status_message.emit("Link removed.")

    def clear_map(self):
        for n in list(self.nodes):
            self.delete_node(n)
        self._id_counter = 0

    # ------------------------------------------------------------------ menus
    def request_rename(self, node):
        text, ok = QInputDialog.getText(
            self.views()[0] if self.views() else None,
            "Rename node", "Title:", text=node.title)
        if ok:
            node.set_title(text)
            self.selection_info_changed.emit()

    def show_node_menu(self, node, screen_pos):
        menu = QMenu()
        menu.addAction("➕  Add child", lambda: self.add_child(node))
        menu.addAction("✏  Rename", lambda: self.request_rename(node))
        menu.addAction("\U0001F517  Start link from here", lambda: self.begin_link(node))

        if self.descendants(node):
            verb = "Expand subtree" if node.collapsed else "Collapse subtree"
            icon = "▸" if node.collapsed else "▾"
            menu.addAction(f"{icon}  {verb}", lambda: self.toggle_collapse(node))

        cat_menu = menu.addMenu("\U0001F3A8  Category")
        for key, cat in CATEGORIES.items():
            cat_menu.addAction(f"{cat.emoji}  {cat.label}",
                               lambda k=key: (node.set_category(k),
                                              self.selection_info_changed.emit()))

        if node.edges:
            unlink = menu.addMenu("✂  Unlink")
            for e in list(node.edges):
                other = e.other(node)
                ocat = get_category(other.category)
                unlink.addAction(f"{ocat.emoji}  {other.title}",
                                 lambda edge=e: self.remove_edge(edge))
            if len(node.edges) > 1:
                unlink.addSeparator()
                unlink.addAction("Remove ALL links", lambda: self.unlink_all(node))

        menu.addSeparator()
        menu.addAction("\U0001F5D1  Delete", lambda: self.delete_node(node))
        menu.exec(screen_pos)

    def show_edge_menu(self, edge, screen_pos):
        menu = QMenu()
        a = get_category(edge.source.category)
        b = get_category(edge.dest.category)
        header = menu.addAction(f"{a.emoji} {edge.source.title}  →  {b.emoji} {edge.dest.title}")
        header.setEnabled(False)
        menu.addSeparator()
        menu.addAction("✂  Remove this link",
                       lambda: (self.remove_edge(edge),
                                self.status_message.emit("Link removed.")))
        menu.exec(screen_pos)

    def unlink_all(self, node):
        for e in list(node.edges):
            self.remove_edge(e)
        self.status_message.emit("Removed all links from node.")

    # ------------------------------------------------------------------ linking
    def set_link_mode(self, on):
        self.link_mode = on
        self._link_source = None
        if on:
            self.status_message.emit("Link mode: click a source node, then a target.")
        else:
            self.status_message.emit("")

    def begin_link(self, node):
        self.link_mode = True
        self._link_source = node
        self.clearSelection()
        node.setSelected(True)
        self.status_message.emit("Now click the target node to connect.")

    def mousePressEvent(self, event):
        if self.link_mode and event.button() == Qt.LeftButton:
            item = self._node_at(event.scenePos())
            if item is not None:
                if self._link_source is None:
                    self._link_source = item
                    self.clearSelection()
                    item.setSelected(True)
                    self.status_message.emit("Now click the target node to connect.")
                else:
                    self.connect_nodes(self._link_source, item)
                    self.status_message.emit("Linked! Click another source, or press L / Esc to stop.")
                    self._link_source = None
                event.accept()
                return
        super().mousePressEvent(event)

    def _node_at(self, scene_pos):
        for item in self.items(scene_pos):
            if isinstance(item, MindNode):
                return item
        return None

    # ------------------------------------------------------------------ layout
    def auto_arrange(self, iterations=160):
        """Light force-directed relaxation so tangled maps untangle themselves."""
        if not self.nodes:
            return
        self.lane_bands = []
        pos = {n: [n.connection_point().x(), n.connection_point().y()] for n in self.nodes}
        k = 240.0
        for _ in range(iterations):
            disp = {n: [0.0, 0.0] for n in self.nodes}
            for i, a in enumerate(self.nodes):
                for b in self.nodes[i + 1:]:
                    dx = pos[a][0] - pos[b][0]
                    dy = pos[a][1] - pos[b][1]
                    dist = math.hypot(dx, dy) or 0.01
                    force = (k * k) / dist
                    ux, uy = dx / dist, dy / dist
                    disp[a][0] += ux * force
                    disp[a][1] += uy * force
                    disp[b][0] -= ux * force
                    disp[b][1] -= uy * force
            for e in self.edges:
                a, b = e.source, e.dest
                dx = pos[a][0] - pos[b][0]
                dy = pos[a][1] - pos[b][1]
                dist = math.hypot(dx, dy) or 0.01
                force = (dist * dist) / k
                ux, uy = dx / dist, dy / dist
                disp[a][0] -= ux * force
                disp[a][1] -= uy * force
                disp[b][0] += ux * force
                disp[b][1] += uy * force
            for n in self.nodes:
                d = disp[n]
                dl = math.hypot(d[0], d[1]) or 0.01
                step = min(dl, 18.0)
                pos[n][0] += d[0] / dl * step
                pos[n][1] += d[1] / dl * step

        for n in self.nodes:
            cx, cy = pos[n]
            n._base = QPointF(cx - n._w / 2, cy - 31)
            n._set_float(n._float)
        for e in self.edges:
            e.adjust()

    def _place(self, node, x, y):
        node._base = QPointF(x, y)
        node._set_float(0.0)

    def tree_layout(self):
        """Layered top-down layout following source→dest edge direction."""
        if not self.nodes:
            return
        self.lane_bands = []
        children = {n: [] for n in self.nodes}
        indeg = {n: 0 for n in self.nodes}
        for e in self.edges:
            children[e.source].append(e.dest)
            indeg[e.dest] += 1
        roots = [n for n in self.nodes if indeg[n] == 0] or [self.nodes[0]]

        levels = {}
        seen = set()

        def walk(n, depth):
            if n in seen:
                return
            seen.add(n)
            levels.setdefault(depth, []).append(n)
            for c in children[n]:
                walk(c, depth + 1)

        for r in roots:
            walk(r, 0)
        for n in self.nodes:                 # cycles / disconnected
            if n not in seen:
                walk(n, 0)

        v_gap, h_gap = 165, 55
        for depth, row in sorted(levels.items()):
            total = sum(n._w for n in row) + h_gap * (len(row) - 1)
            x = -total / 2
            y = depth * v_gap
            for n in row:
                self._place(n, x, y)
                x += n._w + h_gap
        for e in self.edges:
            e.adjust()

    def swimlane_layout(self):
        """One horizontal lane per category, ordered by the kill chain."""
        if not self.nodes:
            return
        lane_keys = [k for k in CATEGORIES if any(n.category == k for n in self.nodes)]
        lane_h = 150
        self.lane_bands = []
        for li, key in enumerate(lane_keys):
            members = [n for n in self.nodes if n.category == key]
            y0 = li * lane_h
            y = y0 + 28
            x = 40
            for n in members:
                self._place(n, x, y)
                x += n._w + 45
            self.lane_bands.append(
                (get_category(key).label, get_category(key).color, y0, y0 + lane_h, x))
        for e in self.edges:
            e.adjust()
        self.invalidate(self.sceneRect(), QGraphicsScene.BackgroundLayer)

    # ------------------------------------------------------------------ LOD / perf
    def set_lod(self, simple):
        if simple == self.simple_lod:
            return
        self.simple_lod = simple
        self._apply_node_effects()
        for n in self.nodes:
            if simple:
                n.pause_float()
            elif len(self.nodes) <= PERF_FLOAT_LIMIT:
                n.resume_float()
            n.update()
        for e in self.edges:
            e.update()

    def set_interaction_fast(self, on):
        """While actively panning/dragging, drop the costly per-frame work:
        the drop-shadow glow (re-blurred every repaint) and the idle float +
        edge-flow animations. Restored to the current LOD/perf state on release.
        """
        if on == self._fast:
            return
        self._fast = on
        if on:
            for n in self.nodes:
                n.set_glow_enabled(False)
                n.pause_float()
        else:
            self._apply_node_effects()
            self.update_performance_mode()

    def update_performance_mode(self):
        self._apply_node_effects()
        floats_ok = len(self.nodes) <= PERF_FLOAT_LIMIT and not self.simple_lod
        for n in self.nodes:
            if floats_ok:
                n.resume_float()
            else:
                n.pause_float()

    def _apply_node_effects(self):
        glow_ok = (not self.simple_lod) and (len(self.nodes) <= PERF_GLOW_LIMIT)
        for n in self.nodes:
            n.set_glow_enabled(glow_ok)

    # ------------------------------------------------------------------ search
    def apply_search(self, text):
        self.search_query = (text or "").strip().lower()
        q = self.search_query
        matches = []
        for n in self.nodes:
            if not q:
                n.dimmed = False
            else:
                hay = f"{n.title} {n.plain_notes()} {get_category(n.category).label}".lower()
                hit = q in hay
                n.dimmed = not hit
                if hit:
                    matches.append(n)
            n.update()
        for e in self.edges:
            e.update()
        return matches

    # ------------------------------------------------------------------ collapse
    def descendants(self, node):
        """Nodes reachable downstream (source→dest) from node, excluding it."""
        out, stack, seen = set(), [node], {node}
        while stack:
            cur = stack.pop()
            for e in cur.edges:
                if e.source is cur and e.dest not in seen:
                    seen.add(e.dest)
                    out.add(e.dest)
                    stack.append(e.dest)
        return out

    def toggle_collapse(self, node):
        node.collapsed = not node.collapsed
        self.refresh_visibility()
        self.status_message.emit(
            "Subtree collapsed." if node.collapsed else "Subtree expanded.")

    def refresh_visibility(self):
        hidden = set()
        for n in self.nodes:
            if n.collapsed:
                hidden |= self.descendants(n)
        for n in self.nodes:
            n.setVisible(n not in hidden)
        for e in self.edges:
            e.setVisible(e.source.isVisible() and e.dest.isVisible())
        for n in self.nodes:
            n.hidden_count = len(self.descendants(n)) if n.collapsed else 0
            n.update()

    # ------------------------------------------------------------------ export
    def content_rect(self):
        rect = QRectF()
        for n in self.nodes:
            if n.isVisible():
                r = n.sceneBoundingRect()
                rect = r if rect.isNull() else rect.united(r)
        return rect

    def render_image(self, path, scale=2.0, margin=60):
        rect = self.content_rect()
        if rect.isNull():
            rect = QRectF(-200, -200, 400, 400)
        rect = rect.adjusted(-margin, -margin, margin, margin)
        img = QImage(int(rect.width() * scale), int(rect.height() * scale),
                     QImage.Format_ARGB32)
        img.fill(QColor(THEME["bg_bottom"]))
        painter = QPainter(img)
        painter.setRenderHint(QPainter.Antialiasing, True)
        self.clearSelection()
        old_scale, self.view_scale = self.view_scale, 1.0   # natural-size node text
        self.render(painter, target=QRectF(0, 0, img.width(), img.height()), source=rect)
        self.view_scale = old_scale
        painter.end()
        return img.save(path)

    def to_markdown(self):
        lines = ["# MindMapo — engagement map", ""]
        for key, cat in CATEGORIES.items():
            members = [n for n in self.nodes if n.category == key]
            if not members:
                continue
            lines.append(f"## {cat.emoji} {cat.label}")
            lines.append("")
            for n in members:
                lines.append(f"- **{n.title}**")
                for ln in (n.plain_notes() or "").splitlines():
                    if ln.strip():
                        lines.append(f"    - {ln.strip()}")
                links = [e.other(n).title for e in n.edges]
                if links:
                    lines.append(f"    - _links:_ " + ", ".join(links))
            lines.append("")
        return "\n".join(lines)

    # ------------------------------------------------------------------ persistence
    def to_dict(self):
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
        }

    def from_dict(self, data):
        self.clear_map()
        by_id = {}
        for nd in data.get("nodes", []):
            node = self.add_node(
                nd.get("category", "note"),
                QPointF(nd.get("x", 0), nd.get("y", 0)),
                title=nd.get("title", ""),
                notes=nd.get("notes", ""),
                animate=True,
                node_id=nd.get("id"),
            )
            by_id[nd.get("id")] = node
        for ed in data.get("edges", []):
            a, b = by_id.get(ed.get("a")), by_id.get(ed.get("b"))
            if a and b:
                self.connect_nodes(a, b)

    # ------------------------------------------------------------------ background
    def drawBackground(self, painter, rect):
        painter.setRenderHint(QPainter.Antialiasing, True)

        # Vertical night gradient.
        grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        grad.setColorAt(0.0, QColor(THEME["bg_top"]))
        grad.setColorAt(1.0, QColor(THEME["bg_bottom"]))
        painter.fillRect(rect, QBrush(grad))

        # Swimlane bands (drawn under everything when in swimlane layout).
        if self.lane_bands:
            for i, (label, color, y0, y1, x_end) in enumerate(self.lane_bands):
                band = QColor(color)
                band.setAlpha(20 if i % 2 == 0 else 32)
                x0 = -40
                width = max(x_end + 80, 600) + 40
                painter.fillRect(QRectF(x0, y0, width, y1 - y0), band)
                painter.setPen(QColor(255, 255, 255, 200))
                painter.setFont(QFont("Segoe UI", 13, QFont.Bold))
                painter.drawText(QRectF(x0 + 12, y0 + 4, 300, 26),
                                 Qt.AlignVCenter | Qt.AlignLeft, label.upper())

        # Drifting parallax stars/dust.
        drift = self._phase * 0.25
        dot = QColor(THEME["grid_dot"])
        painter.setPen(Qt.NoPen)
        for x, y, r, depth in self._stars:
            sx = x + drift * depth
            sy = y
            # wrap within the broad scene rect
            if not rect.adjusted(-50, -50, 50, 50).contains(QPointF(sx, sy)):
                continue
            c = QColor(dot)
            c.setAlpha(int(120 * depth))
            painter.setBrush(c)
            painter.drawEllipse(QPointF(sx, sy), r * depth, r * depth)


LOD_THRESHOLD = 0.55     # below this zoom we drop to simplified rendering


class MindView(QGraphicsView):
    viewport_changed = Signal()

    def __init__(self, scene):
        super().__init__(scene)
        # GPU-accelerated, vsync-synced viewport → tear-free frames presented at
        # the monitor's native refresh rate (the "canvas app" feel). Falls back
        # to the software raster viewport if OpenGL isn't available (e.g. the
        # headless "offscreen" platform used for tests).
        try:
            from PySide6.QtWidgets import QApplication
            if QApplication.platformName() != "offscreen":
                from PySide6.QtOpenGLWidgets import QOpenGLWidget
                self.setViewport(QOpenGLWidget())
        except Exception:
            pass
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform |
                            QPainter.TextAntialiasing)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._zoom = 1.0
        self._panning = False
        self._pan_moved = False
        self._suppress_menu = False
        self._pan_start = QPointF()
        self._pan_rem = QPointF(0, 0)
        self.centerOn(0, 0)
        self.horizontalScrollBar().valueChanged.connect(self.viewport_changed)
        self.verticalScrollBar().valueChanged.connect(self.viewport_changed)

    def _after_view_change(self):
        self._zoom = self.transform().m11()
        self.scene().view_scale = self._zoom
        self.scene().set_lod(self._zoom < LOD_THRESHOLD)
        self.viewport_changed.emit()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.viewport_changed.emit()

    # ----- zoom
    def wheelEvent(self, event):
        factor = 1.06 if event.angleDelta().y() > 0 else 1 / 1.06
        new_zoom = self._zoom * factor
        if 0.25 < new_zoom < 3.2:
            self.scale(factor, factor)
            self._after_view_change()

    def reset_zoom(self):
        self.resetTransform()
        self._after_view_change()

    def fit_all(self):
        scene = self.scene()
        visible = [n for n in scene.nodes if n.isVisible()]
        if visible:
            rect = QRectF()
            for n in visible:
                r = n.sceneBoundingRect()
                rect = r if rect.isNull() else rect.united(r)
            self.fitInView(rect.adjusted(-80, -80, 80, 80), Qt.KeepAspectRatio)
            self._after_view_change()
        else:
            self.resetTransform()
            self.centerOn(0, 0)
            self._after_view_change()

    # ----- pan: middle mouse, Alt+drag, or right-drag on empty canvas
    def mousePressEvent(self, event):
        want_pan = event.button() == Qt.MiddleButton or (
            event.button() == Qt.LeftButton and event.modifiers() & Qt.AltModifier)
        # A right-press on empty canvas grabs and drags the map. Right-clicking a
        # node/edge (item present) still opens its context menu.
        if (not want_pan and event.button() == Qt.RightButton
                and self.itemAt(event.position().toPoint()) is None):
            want_pan = True
        if want_pan:
            self._panning = True
            self._pan_moved = False
            self._pan_start = event.position()
            self._pan_rem = QPointF(0, 0)
            self.setCursor(Qt.ClosedHandCursor)
            self.scene().set_interaction_fast(True)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._panning:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            if abs(delta.x()) + abs(delta.y()) > 2:
                self._pan_moved = True
            # Carry sub-pixel remainders across moves so the pan tracks the
            # cursor exactly instead of drifting from repeated int() truncation.
            dx = delta.x() + self._pan_rem.x()
            dy = delta.y() + self._pan_rem.y()
            ix, iy = int(dx), int(dy)
            self._pan_rem = QPointF(dx - ix, dy - iy)
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - ix)
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - iy)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._panning:
            self._panning = False
            self.setCursor(Qt.ArrowCursor)
            # Swallow the context menu that a right-drag would otherwise pop.
            self._suppress_menu = (event.button() == Qt.RightButton and self._pan_moved)
            self.scene().set_interaction_fast(False)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):
        # Don't show a menu for the right-drag we just used to pan.
        if getattr(self, "_suppress_menu", False):
            self._suppress_menu = False
            event.accept()
            return
        super().contextMenuEvent(event)
