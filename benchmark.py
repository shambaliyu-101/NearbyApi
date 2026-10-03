import math
import random
import time
from typing import List, Tuple
from quadtree import QuadTree, BoundingBox, SpatialItem


def linear_scan_nearest(
    items: List[SpatialItem], target_x: float, target_y: float, k: int = 5
) -> List[Tuple[SpatialItem, float]]:
    """Brute force O(N log k) / O(N) linear scan for baseline comparison."""
    distances = [(item, item.distance_to(target_x, target_y)) for item in items]
    distances.sort(key=lambda pair: pair[1])
    return distances[:k]


def linear_scan_range(
    items: List[SpatialItem], min_x: float, min_y: float, max_x: float, max_y: float
) -> List[SpatialItem]:
    """Brute force O(N) range check across all items."""
    search_box = BoundingBox(min_x, min_y, max_x, max_y)
    return [item for item in items if search_box.intersects(item.bounds)]


def run_spatial_benchmark(num_items: int = 20000, num_queries: int = 200):
    print("=" * 65)
    print(f"SPATIAL BENCHMARK: QuadTree vs. Linear Scan")
    print(f"Dataset: {num_items:,} locations | Sample Queries: {num_queries}")
    print("=" * 65)

    random.seed(42)
    world_bounds = BoundingBox(0.0, 0.0, 1000.0, 1000.0)

    # Generate synthetic points
    print(f"Generating {num_items:,} random spatial points...")
    raw_items = [
        SpatialItem(
            item_id=f"loc_{i}",
            x=random.uniform(0.0, 1000.0),
            y=random.uniform(0.0, 1000.0),
        )
        for i in range(num_items)
    ]

    # Benchmark QuadTree build / insertion time
    start_time = time.perf_counter()
    tree = QuadTree(world_bounds, capacity=8, max_depth=12)
    for item in raw_items:
        tree.insert(item)
    build_time = time.perf_counter() - start_time
    print(f"QuadTree indexed {num_items:,} items in: {build_time:.4f}s\n")

    # Generate sample query points
    queries = [
        (random.uniform(100.0, 900.0), random.uniform(100.0, 900.0))
        for _ in range(num_queries)
    ]

    # -------------------------------------------------------------
    # Test A: k-Nearest Neighbor (k=5)
    # -------------------------------------------------------------
    print("Running k-NN queries (k=5)...")

    # Linear scan
    t0 = time.perf_counter()
    for qx, qy in queries:
        _ = linear_scan_nearest(raw_items, qx, qy, k=5)
    linear_knn_time = time.perf_counter() - t0

    # Quadtree
    t0 = time.perf_counter()
    for qx, qy in queries:
        _ = tree.query_nearest(qx, qy, k=5)
    quadtree_knn_time = time.perf_counter() - t0

    knn_speedup = linear_knn_time / quadtree_knn_time

    print(f"  • Linear Scan Total:    {linear_knn_time:.4f}s (avg: {(linear_knn_time/num_queries)*1000:.3f} ms/query)")
    print(f"  • QuadTree Index Total: {quadtree_knn_time:.4f}s (avg: {(quadtree_knn_time/num_queries)*1000:.3f} ms/query)")
    print(f"  --> Speedup: {knn_speedup:.2f}x faster with QuadTree!\n")

    
    # Test B: Range Search (50x50 Bounding Box)
    
    print("Running Bounding Box Range queries...")

    range_boxes = [
        (qx - 25.0, qy - 25.0, qx + 25.0, qy + 25.0)
        for qx, qy in queries
    ]

    # Linear scan
    t0 = time.perf_counter()
    for min_x, min_y, max_x, max_y in range_boxes:
        _ = linear_scan_range(raw_items, min_x, min_y, max_x, max_y)
    linear_range_time = time.perf_counter() - t0

    # Quadtree
    t0 = time.perf_counter()
    for min_x, min_y, max_x, max_y in range_boxes:
        _ = tree.query_range(min_x, min_y, max_x, max_y)
    quadtree_range_time = time.perf_counter() - t0

    range_speedup = linear_range_time / quadtree_range_time

    print(f"  • Linear Scan Total:    {linear_range_time:.4f}s (avg: {(linear_range_time/num_queries)*1000:.3f} ms/query)")
    print(f"  • QuadTree Index Total: {quadtree_range_time:.4f}s (avg: {(quadtree_range_time/num_queries)*1000:.3f} ms/query)")
    print(f"  --> Speedup: {range_speedup:.2f}x faster with QuadTree!")
    print("=" * 65)


if __name__ == "__main__":
    run_spatial_benchmark()