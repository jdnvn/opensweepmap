from typing import Any
from sqlalchemy import Column, Integer, String, Time, Boolean, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from geoalchemy2 import Geometry
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Schedule(Base):
    __tablename__ = 'schedules'

    id = Column(Integer, primary_key=True)
    street_name = Column(String)
    street_id = Column(Integer, ForeignKey('streets.id'))
    suburb_name = Column(String)
    side = Column(String)
    start_time = Column(Time)
    end_time = Column(Time)
    from_street_name = Column(String)
    from_street_id = Column(Integer, ForeignKey('streets.id'))
    to_street_name = Column(String)
    to_street_id = Column(Integer, ForeignKey('streets.id'))
    has_duplicates = Column(Boolean)
    one_way = Column(Boolean)
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


class Sidewalk(Base):
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
