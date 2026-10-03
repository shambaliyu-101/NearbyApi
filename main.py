from starlette.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os

from typing import List, Optional
from uuid import UUID

from fastapi import FastAPI, Depends, HTTPException, Query, status
from jose import JWTError
from sqlalchemy.orm import Session

from database import get_db, engine
from models import Base, User, Region, Location, LocationType
from schemas import (
    UserCreate,
    UserOut,
    LoginRequest,
    TokenPair,
    RefreshRequest,
    AccessToken,
    RegionCreate,
    RegionOut,
    LocationCreate,
    LocationUpdate,
    LocationOut,
    NearbyResult,
)
from auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from dependencies import get_current_user
from quadtree import QuadTree, BoundingBox, SpatialItem

# Ensure tables are created
Base.metadata.create_all(bind=engine)

app = FastAPI(title="NearbyAPI")

# Mount static files folder
if os.path.isdir("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")
# ================= ROOT =================
@app.get("/", include_in_schema=False)
def read_root():
    return FileResponse("static/index.html")

# ================= AUTH =================
@app.post("/auth/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/auth/login", response_model=TokenPair)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()

    invalid_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect email or password",
    )

    if not user or not verify_password(payload.password, user.hashed_password):
        raise invalid_credentials

    user_id = str(user.id)
    return TokenPair(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )


@app.post("/auth/refresh", response_model=AccessToken)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    invalid_token = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
    )

    try:
        decoded = decode_token(payload.refresh_token)
    except JWTError:
        raise invalid_token

    if decoded.get("type") != "refresh":
        raise invalid_token

    user_id = decoded.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise invalid_token

    return AccessToken(access_token=create_access_token(user_id))


@app.get("/auth/me", response_model=UserOut)
def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user


# ================= REGIONS =================
@app.post("/regions", response_model=RegionOut, status_code=status.HTTP_201_CREATED)
def create_region(
    payload: RegionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    region = Region(
        name=payload.name,
        owner_id=current_user.id,
    )
    db.add(region)
    db.commit()
    db.refresh(region)
    return region


@app.get("/regions", response_model=List[RegionOut])
def list_regions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Region).filter(Region.owner_id == current_user.id).all()


@app.get("/regions/{region_id}", response_model=RegionOut)
def get_region(
    region_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    region = db.query(Region).filter(Region.id == region_id).first()
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")
    if region.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this region")
    return region


@app.delete("/regions/{region_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_region(
    region_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    region = db.query(Region).filter(Region.id == region_id).first()
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")
    if region.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this region")

    db.delete(region)
    db.commit()
    return None


# ================= LOCATIONS CRUD =================
@app.post(
    "/regions/{region_id}/locations",
    response_model=LocationOut,
    status_code=status.HTTP_201_CREATED,
)
def create_location(
    region_id: UUID,
    payload: LocationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    region = db.query(Region).filter(Region.id == region_id).first()
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")
    if region.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this region")

    loc = Location(
        region_id=region_id,
        location_type=LocationType(payload.location_type.value),
        x=payload.x,
        y=payload.y,
        width=payload.width,
        height=payload.height,
        radius=payload.radius,
    )
    db.add(loc)
    db.commit()
    db.refresh(loc)
    return loc


@app.get("/regions/{region_id}/locations", response_model=List[LocationOut])
def list_locations_in_region(
    region_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    region = db.query(Region).filter(Region.id == region_id).first()
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")
    if region.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this region")

    return db.query(Location).filter(Location.region_id == region_id).all()


@app.put("/locations/{location_id}", response_model=LocationOut)
def update_location(
    location_id: UUID,
    payload: LocationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    loc = db.query(Location).filter(Location.id == location_id).first()
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")

    if loc.region.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this location")

    update_data = payload.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(loc, field, val)

    db.commit()
    db.refresh(loc)
    return loc


@app.delete("/locations/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_location(
    location_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    loc = db.query(Location).filter(Location.id == location_id).first()
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")

    if loc.region.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this location")

    db.delete(loc)
    db.commit()
    return None


# ================= SPATIAL QUERIES =================
def _build_region_quadtree(locations: List[Location]) -> Optional[QuadTree]:
    """Builds an in-memory QuadTree dynamically sized to fit all locations in a region."""
    if not locations:
        return None

    # Derive bounding box that encompasses all items with some padding
    min_x = min(loc.x - (loc.radius or (loc.width or 0) / 2) for loc in locations)
    max_x = max(loc.x + (loc.radius or (loc.width or 0) / 2) for loc in locations)
    min_y = min(loc.y - (loc.radius or (loc.height or 0) / 2) for loc in locations)
    max_y = max(loc.y + (loc.radius or (loc.height or 0) / 2) for loc in locations)

    # Add margin so items on outer boundaries fit cleanly
    padding = max((max_x - min_x) * 0.1, (max_y - min_y) * 0.1, 10.0)
    boundary = BoundingBox(
        min_x - padding,
        min_y - padding,
        max_x + padding,
        max_y + padding,
    )

    tree = QuadTree(boundary=boundary, capacity=4)
    for loc in locations:
        item = SpatialItem(
            item_id=str(loc.id),
            x=loc.x,
            y=loc.y,
            location_type=loc.location_type.value,
            width=loc.width,
            height=loc.height,
            radius=loc.radius,
            data=loc,
        )
        tree.insert(item)

    return tree


@app.get("/regions/{region_id}/search", response_model=List[LocationOut])
def search_region(
    region_id: UUID,
    x1: float = Query(..., description="Min X / Longitude coordinate"),
    y1: float = Query(..., description="Min Y / Latitude coordinate"),
    x2: float = Query(..., description="Max X / Longitude coordinate"),
    y2: float = Query(..., description="Max Y / Latitude coordinate"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """The range query finds all points or zones within the bounding box [x1, y1] to [x2, y2]."""
    region = db.query(Region).filter(Region.id == region_id).first()
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")
    if region.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this region")

    locations = db.query(Location).filter(Location.region_id == region_id).all()
    tree = _build_region_quadtree(locations)
    if not tree:
        return []

    min_x, max_x = min(x1, x2), max(x1, x2)
    min_y, max_y = min(y1, y2), max(y1, y2)

    matched_items = tree.query_range(min_x, min_y, max_x, max_y)
    return [item.data for item in matched_items]


@app.get("/regions/{region_id}/nearby", response_model=List[NearbyResult])
def nearby_search(
    region_id: UUID,
    x: float = Query(..., description="Target X coordinate"),
    y: float = Query(..., description="Target Y coordinate"),
    limit: int = Query(5, ge=1, le=50, description="Max closest locations to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """The nearest neighbor query: finds the k closest locations to (x, y)."""
    region = db.query(Region).filter(Region.id == region_id).first()
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")
    if region.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this region")

    locations = db.query(Location).filter(Location.region_id == region_id).all()
    tree = _build_region_quadtree(locations)
    if not tree:
        return []

    nearest_items = tree.query_nearest(x, y, k=limit)
    return [
        NearbyResult(location=item.data, distance=round(dist, 4))
        for item, dist in nearest_items
    ]


@app.get("/locations/{location_id}/overlaps", response_model=List[LocationOut])
def check_overlaps(
    location_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Finds all existing zones/locations that geometrically collide with this location."""
    target_loc = db.query(Location).filter(Location.id == location_id).first()
    if not target_loc:
        raise HTTPException(status_code=404, detail="Location not found")
    if target_loc.region.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this location")

    # Fetch all locations in the same region
    locations = db.query(Location).filter(Location.region_id == target_loc.region_id).all()
    tree = _build_region_quadtree(locations)
    if not tree:
        return []

    target_item = SpatialItem(
        item_id=str(target_loc.id),
        x=target_loc.x,
        y=target_loc.y,
        location_type=target_loc.location_type.value,
        width=target_loc.width,
        height=target_loc.height,
        radius=target_loc.radius,
        data=target_loc,
    )

    overlapping_items = tree.query_overlaps(target_item)
    return [item.data for item in overlapping_items]