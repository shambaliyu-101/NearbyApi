from quadtree import QuadTree, BoundingBox, SpatialItem


def test_quadtree():
    print("Testing QuadTree Range and Nearest-Neighbor...")
    
    # Boundary covering [0, 0] to [100, 100]
    boundary = BoundingBox(0, 0, 100, 100)
    tree = QuadTree(boundary, capacity=2)

    # Insert 5 points (drivers)
    points = [
        SpatialItem("driver_1", 10.0, 10.0),
        SpatialItem("driver_2", 12.0, 15.0),
        SpatialItem("driver_3", 50.0, 50.0),
        SpatialItem("driver_4", 80.0, 80.0),
        SpatialItem("driver_5", 11.0, 11.0),
    ]

    for p in points:
        assert tree.insert(p) is True

    # 1. Test Range Query: Box [0, 0] to [20, 20]
    range_results = tree.query_range(0, 0, 20, 20)
    found_ids = {item.item_id for item in range_results}
    print(f"Range Query found: {found_ids}")
    assert found_ids == {"driver_1", "driver_2", "driver_5"}

    # 2. Test Nearest Neighbor: Closest to (10, 10), k=2
    nearest = tree.query_nearest(10.0, 10.0, k=2)
    nearest_ids = [item.item_id for item, dist in nearest]
    print(f"Nearest 2 to (10, 10): {nearest_ids}")
    assert nearest_ids[0] == "driver_1"
    assert nearest_ids[1] == "driver_5"

    # 3. Test Overlap: Circles
    zone_a = SpatialItem("zone_a", 50.0, 50.0, location_type="zone", radius=10.0)
    zone_b = SpatialItem("zone_b", 55.0, 50.0, location_type="zone", radius=10.0)  # Overlaps A
    zone_c = SpatialItem("zone_c", 90.0, 90.0, location_type="zone", radius=5.0)   # Far away

    tree_zones = QuadTree(boundary)
    tree_zones.insert(zone_a)
    tree_zones.insert(zone_c)

    overlaps = tree_zones.query_overlaps(zone_b)
    overlap_ids = [item.item_id for item in overlaps]
    print(f"Overlaps with zone_b: {overlap_ids}")
    assert overlap_ids == ["zone_a"]

    print(" ALL TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    test_quadtree()