import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import (
    Column, String, Float, ForeignKey, DateTime, Enum as SAEnum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


def uuid_pk():
    return Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class LocationType(str, PyEnum):
    POINT = "point"
    ZONE = "zone"


class User(Base):
    __tablename__ = "users"

    id = uuid_pk()
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    regions = relationship("Region", back_populates="owner", cascade="all, delete-orphan")


class Region(Base):
    __tablename__ = "regions"

    id = uuid_pk()
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    owner = relationship("User", back_populates="regions")
    locations = relationship("Location", back_populates="region", cascade="all, delete-orphan")


class Location(Base):
    __tablename__ = "locations"

    id = uuid_pk()
    region_id = Column(UUID(as_uuid=True), ForeignKey("regions.id"), nullable=False, index=True)
    location_type = Column(SAEnum(LocationType), nullable=False)

    x = Column(Float, nullable=False)
    y = Column(Float, nullable=False)

    # zone-only fields (nullable for points)
    width = Column(Float, nullable=True)
    height = Column(Float, nullable=True)
    radius = Column(Float, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    region = relationship("Region", back_populates="locations")


