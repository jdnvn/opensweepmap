from typing import Any
from sqlalchemy import Column, Integer, String, Time, Boolean, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from geoalchemy2 import Geometry
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class BaseModel(Base):
    __abstract__ = True  # This class will not be created in the database

    def as_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}


class Schedule(BaseModel):
    __tablename__ = 'schedules'

    id = Column(Integer, primary_key=True)
    street_name = Column(String)
    street_id = Column(Integer, ForeignKey('streets.id'))
    suburb_name = Column(String)
    side = Column(String)
    from_street_name = Column(String)
    from_street_id = Column(Integer, ForeignKey('streets.id'))
    to_street_name = Column(String)
    to_street_id = Column(Integer, ForeignKey('streets.id'))
    has_duplicates = Column(Boolean)
    one_way = Column(Boolean)
    start_time = Column(Time)
    end_time = Column(Time)
    week_1 = Column(Boolean)
    week_2 = Column(Boolean)
    week_3 = Column(Boolean)
    week_4 = Column(Boolean)
    week_5 = Column(Boolean)
    sunday = Column(Boolean)
    monday = Column(Boolean)
    tuesday = Column(Boolean)
    wednesday = Column(Boolean)
    thursday = Column(Boolean)
    friday = Column(Boolean)
    saturday = Column(Boolean)
    every_day = Column(Boolean)
    year_round = Column(Boolean)
    north_end_pilot = Column(Boolean)


class Sidewalk(BaseModel):
    __tablename__ = 'sidewalks'

    id = Column(Integer, primary_key=True)
    schedule_id = Column(Integer, ForeignKey('schedules.id'))
    status = Column(String)
    geometry: Mapped[Any] = mapped_column(
        Geometry(
            "LINESTRING",  # Change from POINT to LINESTRING
            srid=4326,
            spatial_index=False,
            name="geometry",
        ),
        nullable=False,
    )
    schedule = relationship("Schedule", backref="sidewalks")


class User(BaseModel):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String)

    def as_dict(self):
        user_dict = super().as_dict()
        user_dict.pop('hashed_password', None)
        return user_dict
