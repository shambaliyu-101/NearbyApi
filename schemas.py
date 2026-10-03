from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, model_validator


# ================= USER SCHEMAS =================
class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: UUID
    email: EmailStr

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class AccessToken(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ================= REGION SCHEMAS =================
class RegionCreate(BaseModel):
    name: str


class RegionOut(BaseModel):
    id: UUID
    name: str
    owner_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


# ================= LOCATION SCHEMAS =================
class LocationTypeEnum(str, Enum):
    point = "point"
    zone = "zone"


class LocationCreate(BaseModel):
    location_type: LocationTypeEnum
    x: float
    y: float
    width: Optional[float] = None
    height: Optional[float] = None
    radius: Optional[float] = None

    @model_validator(mode="after")
    def validate_zone_dimensions(self):
        if self.location_type == LocationTypeEnum.zone:
            has_rect = self.width is not None and self.height is not None
            has_circle = self.radius is not None
            if not has_rect and not has_circle:
                raise ValueError(
                    "Zones must specify either (width and height) for a rectangle, or radius for a circle."
                )
        return self


class LocationUpdate(BaseModel):
    x: Optional[float] = None
    y: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    radius: Optional[float] = None


class LocationOut(BaseModel):
    id: UUID
    region_id: UUID
    location_type: LocationTypeEnum
    x: float
    y: float
    width: Optional[float] = None
    height: Optional[float] = None
    radius: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


class NearbyResult(BaseModel):
    location: LocationOut
    distance: float