import math
import heapq
from typing import List, Optional, Any, Tuple


class BoundingBox:

    def __init__(self, min_x: float, min_y: float, max_x: float, max_y: float):
        if min_x > max_x or min_y > max_y:
            raise ValueError("Invalid bounding box: min coordinates cannot exceed max.")
        self.min_x = min_x
        self.min_y = min_y
        self.max_x = max_x
        self.max_y = max_y

    def contains_point(self, x: float, y: float) -> bool:
        """Returns True if point (x, y) is inside or on the boundary of the box."""
        return self.min_x <= x <= self.max_x and self.min_y <= y <= self.max_y

    def intersects(self, other: "BoundingBox") -> bool:
        """Returns True if this box intersects another bounding box."""
        return not (
            self.max_x < other.min_x
            or self.min_x > other.max_x
            or self.max_y < other.min_y
            or self.min_y > other.max_y
        )

    def distance_to_point(self, x: float, y: float) -> float:
        """Returns minimum Euclidean distance from point (x, y) to closest edge of this box."""
        dx = max(self.min_x - x, 0.0, x - self.max_x)
        dy = max(self.min_y - y, 0.0, y - self.max_y)
        return math.hypot(dx, dy)


class SpatialItem:
    """Represents a point or zone indexed inside the QuadTree."""

    def __init__(
        self,
        item_id: Any,
        x: float,
        y: float,
        location_type: str = "point",
        width: Optional[float] = None,
        height: Optional[float] = None,
        radius: Optional[float] = None,
        data: Any = None,
    ):
        self.item_id = item_id
        self.x = x
        self.y = y
        self.location_type = location_type
        self.width = width
        self.height = height
        self.radius = radius
        self.data = data
        self.bounds = self._compute_bounds()

    def _compute_bounds(self) -> BoundingBox:
        """Computes the conservative AABB for broad-phase filtering."""
        if self.location_type == "point":
            return BoundingBox(self.x, self.y, self.x, self.y)

        # Circular zone
        if self.radius is not None:
            r = self.radius
            return BoundingBox(self.x - r, self.y - r, self.x + r, self.y + r)

        # Rectangular zone (centered at x, y)
        w = self.width if self.width is not None else 0.0
        h = self.height if self.height is not None else 0.0
        half_w = w / 2.0
        half_h = h / 2.0
        return BoundingBox(self.x - half_w, self.y - half_h, self.x + half_w, self.y + half_h)

    def distance_to(self, target_x: float, target_y: float) -> float:
        return math.hypot(self.x - target_x, self.y - target_y)

    def intersects(self, other: "SpatialItem") -> bool:
        """Performs exact narrow-phase geometric collision check."""
        # 1. Quick check: if bounding boxes don't intersect, shapes cannot intersect
        if not self.bounds.intersects(other.bounds):
            return False

        # 2. Point vs Point
        if self.location_type == "point" and other.location_type == "point":
            return math.isclose(self.x, other.x) and math.isclose(self.y, other.y)

        # 3. Circle vs Circle
        if self.radius is not None and other.radius is not None:
            d = math.hypot(self.x - other.x, self.y - other.y)
            return d <= (self.radius + other.radius)

        # 4. Rect vs Rect (AABB vs AABB)
        if (
            self.width is not None
            and self.height is not None
            and other.width is not None
            and other.height is not None
        ):
            return self.bounds.intersects(other.bounds)

        # 5. Circle vs Rect
        circle = self if self.radius is not None else other
        rect = other if self.radius is not None else self

        # Distance from circle center to rectangle bounds
        dist = rect.bounds.distance_to_point(circle.x, circle.y)
        return dist <= circle.radius


class QuadTreeNode:
    """A single node in the QuadTree representing a quadrant."""

    def __init__(self, boundary: BoundingBox, capacity: int = 4, max_depth: int = 10, depth: int = 0):
        self.boundary = boundary
        self.capacity = capacity
        self.max_depth = max_depth
        self.depth = depth

        self.items: List[SpatialItem] = []
        self.divided: bool = False

        self.nw: Optional["QuadTreeNode"] = None
        self.ne: Optional["QuadTreeNode"] = None
        self.sw: Optional["QuadTreeNode"] = None
        self.se: Optional["QuadTreeNode"] = None

    def subdivide(self) -> None:
        """Divides node into four child quadrants: NW, NE, SW, SE."""
        min_x, min_y = self.boundary.min_x, self.boundary.min_y
        max_x, max_y = self.boundary.max_x, self.boundary.max_y
        mid_x = (min_x + max_x) / 2.0
        mid_y = (min_y + max_y) / 2.0

        next_depth = self.depth + 1
        self.nw = QuadTreeNode(BoundingBox(min_x, mid_y, mid_x, max_y), self.capacity, self.max_depth, next_depth)
        self.ne = QuadTreeNode(BoundingBox(mid_x, mid_y, max_x, max_y), self.capacity, self.max_depth, next_depth)
        self.sw = QuadTreeNode(BoundingBox(min_x, min_y, mid_x, mid_y), self.capacity, self.max_depth, next_depth)
        self.se = QuadTreeNode(BoundingBox(mid_x, min_y, max_x, mid_y), self.capacity, self.max_depth, next_depth)

        self.divided = True

        # Redistribute existing items to child quadrants if they fit entirely
        remaining_items = []
        for item in self.items:
            if not self._insert_into_children(item):
                remaining_items.append(item)
        self.items = remaining_items

    def _insert_into_children(self, item: SpatialItem) -> bool:
        """Attempts to push an item down into a specific child quadrant if it fits entirely."""
        for child in (self.nw, self.ne, self.sw, self.se):
            if (
                child.boundary.min_x <= item.bounds.min_x
                and item.bounds.max_x <= child.boundary.max_x
                and child.boundary.min_y <= item.bounds.min_y
                and item.bounds.max_y <= child.boundary.max_y
            ):
                return child.insert(item)
        return False

    def insert(self, item: SpatialItem) -> bool:
        """Inserts a spatial item into this node or its descendants."""
        # Broad-phase check: does item touch this quadrant?
        if not self.boundary.intersects(item.bounds):
            return False

        if not self.divided:
            if len(self.items) < self.capacity or self.depth >= self.max_depth:
                self.items.append(item)
                return True
            self.subdivide()

        # Try inserting into child quadrants
        if self._insert_into_children(item):
            return True

        # If it spans quadrant boundaries, retain it at this node level
        self.items.append(item)
        return True

    def query_range(self, search_box: BoundingBox, results: List[SpatialItem]) -> None:
        """Prunes tree branches not touching search_box; gathers matching items."""
        if not self.boundary.intersects(search_box):
            return

        for item in self.items:
            if search_box.intersects(item.bounds):
                results.append(item)

        if self.divided:
            self.nw.query_range(search_box, results)
            self.ne.query_range(search_box, results)
            self.sw.query_range(search_box, results)
            self.se.query_range(search_box, results)


class QuadTree:
    """The root QuadTree index managing spatial insertions and queries."""

    def __init__(self, boundary: BoundingBox, capacity: int = 4, max_depth: int = 10):
        self.boundary = boundary
        self.root = QuadTreeNode(boundary, capacity=capacity, max_depth=max_depth)
        self.all_items: List[SpatialItem] = []

    def insert(self, item: SpatialItem) -> bool:
        if self.root.insert(item):
            self.all_items.append(item)
            return True
        return False

    def query_range(self, min_x: float, min_y: float, max_x: float, max_y: float) -> List[SpatialItem]:
        """Returns all items whose bounding box intersects [min_x, min_y, max_x, max_y]."""
        search_box = BoundingBox(min_x, min_y, max_x, max_y)
        results: List[SpatialItem] = []
        self.root.query_range(search_box, results)
        return results

    def query_nearest(self, x: float, y: float, k: int = 5) -> List[Tuple[SpatialItem, float]]:
        """
        Finds the k-nearest points/items using Best-First Branch-and-Bound search with a min-heap priority queue.
        Guarantees $O(k \\log N)$ average complexity.
        """
        if k <= 0 or not self.all_items:
            return []

        # Min-heap stores: (distance, counter, node_or_item_flag, object)
        heap = []
        counter = 0

        # Start at root
        init_dist = self.root.boundary.distance_to_point(x, y)
        heapq.heappush(heap, (init_dist, counter, True, self.root))
        counter += 1

        best_candidates: List[Tuple[float, SpatialItem]] = []  # stores (-distance, item) for max-heap of k-best

        while heap:
            dist, _, is_node, entity = heapq.heappop(heap)

            # If we already have k items and this node/item's min distance is further than our worst, prune!
            if len(best_candidates) == k and dist > -best_candidates[0][0]:
                break

            if is_node:
                node: QuadTreeNode = entity
                # Check items stored directly on this node
                for item in node.items:
                    item_dist = item.distance_to(x, y)
                    counter += 1
                    heapq.heappush(heap, (item_dist, counter, False, item))

                # Push children into heap ordered by their distance to (x, y)
                if node.divided:
                    for child in (node.nw, node.ne, node.sw, node.se):
                        child_dist = child.boundary.distance_to_point(x, y)
                        counter += 1
                        heapq.heappush(heap, (child_dist, counter, True, child))
            else:
                item: SpatialItem = entity
                # We popped an actual item
                if len(best_candidates) < k:
                    heapq.heappush(best_candidates, (-dist, item))
                else:
                    if dist < -best_candidates[0][0]:
                        heapq.heappushpop(best_candidates, (-dist, item))

        # Sort closest first
        sorted_results = [(item, -neg_dist) for neg_dist, item in best_candidates]
        sorted_results.sort(key=lambda pair: pair[1])
        return sorted_results

    def query_overlaps(self, target_item: SpatialItem) -> List[SpatialItem]:
        """
        Finds all items that geometrically overlap with target_item.
        Uses broad-phase tree bounding-box query, then narrow-phase exact geometry test.
        """
        candidates: List[SpatialItem] = []
        self.root.query_range(target_item.bounds, candidates)

        overlapping = []
        for candidate in candidates:
            if candidate.item_id == target_item.item_id:
                continue  # Don't collide with self
            if target_item.intersects(candidate):
                overlapping.append(candidate)

        return overlapping