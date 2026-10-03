import pytest
from quadtree import QuadTree, BoundingBox, SpatialItem


def test_bounding_box_contains_and_intersects():
    box = BoundingBox(0.0, 0.0, 10.0, 10.0)
    assert box.contains_point(5.0, 5.0) is True
    assert box.contains_point(10.0, 10.0) is True  # Boundary inclusive
    assert box.contains_point(11.0, 5.0) is False

    overlapping_box = BoundingBox(5.0, 5.0, 15.0, 15.0)
    disjoint_box = BoundingBox(20.0, 20.0, 30.0, 30.0)

    assert box.intersects(overlapping_box) is True
    assert box.intersects(disjoint_box) is False


def test_invalid_bounding_box():
    with pytest.raises(ValueError):
        BoundingBox(10.0, 10.0, 0.0, 0.0)


def test_quadtree_subdivision_and_capacity():
    bounds = BoundingBox(0.0, 0.0, 100.0, 100.0)
    tree = QuadTree(bounds, capacity=2, max_depth=4)

    # Insert items that trigger subdivision
    tree.insert(SpatialItem("p1", 10.0, 10.0))
    tree.insert(SpatialItem("p2", 20.0, 20.0))
    assert tree.root.divided is False

    tree.insert(SpatialItem("p3", 30.0, 30.0))
    assert tree.root.divided is True


def test_range_query_filtering():
    bounds = BoundingBox(0.0, 0.0, 100.0, 100.0)
    tree = QuadTree(bounds, capacity=4)

    tree.insert(SpatialItem("inside_1", 10.0, 10.0))
    tree.insert(SpatialItem("inside_2", 15.0, 15.0))
    tree.insert(SpatialItem("outside", 90.0, 90.0))

    results = tree.query_range(0.0, 0.0, 25.0, 25.0)
    matched_ids = {item.item_id for item in results}

    assert matched_ids == {"inside_1", "inside_2"}
    assert "outside" not in matched_ids


def test_knn_accuracy():
    bounds = BoundingBox(0.0, 0.0, 100.0, 100.0)
    tree = QuadTree(bounds, capacity=2)

    tree.insert(SpatialItem("target", 50.0, 50.0))
    tree.insert(SpatialItem("close", 51.0, 50.0))
    tree.insert(SpatialItem("medium", 60.0, 50.0))
    tree.insert(SpatialItem("far", 90.0, 90.0))

    # Query closest 2 to (50, 50)
    results = tree.query_nearest(50.0, 50.0, k=2)
    assert len(results) == 2
    assert results[0][0].item_id == "target"
    assert pytest.approx(results[0][1], 0.001) == 0.0
    assert results[1][0].item_id == "close"
    assert pytest.approx(results[1][1], 0.001) == 1.0


def test_circle_circle_and_circle_rect_overlap():
    bounds = BoundingBox(0.0, 0.0, 200.0, 200.0)
    tree = QuadTree(bounds)

    circle_a = SpatialItem("c_a", 50.0, 50.0, location_type="zone", radius=10.0)
    circle_b = SpatialItem("c_b", 65.0, 50.0, location_type="zone", radius=10.0)  # Overlaps A
    circle_c = SpatialItem("c_c", 150.0, 150.0, location_type="zone", radius=5.0)  # Disjoint

    rect_a = SpatialItem("r_a", 50.0, 50.0, location_type="zone", width=10.0, height=10.0)

    tree.insert(circle_a)
    tree.insert(circle_c)
    tree.insert(rect_a)

    overlaps = tree.query_overlaps(circle_b)
    overlap_ids = {item.item_id for item in overlaps}

    assert "c_a" in overlap_ids
    assert "c_c" not in overlap_ids