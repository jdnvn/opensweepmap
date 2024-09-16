from sqlalchemy import Column, Integer, String, Time, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Schedule(Base):
    __tablename__ = 'schedules'

    id = Column(Integer, primary_key=True)
    street_name = Column(String)
    suburb_name = Column(String)
    side = Column(String)
    start_time = Column(Time)
    end_time = Column(Time)
    from_street_name = Column(String)
    to_street_name = Column(String)
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
    geometry = Column(Geometry('LINESTRING'))
    schedule = relationship("Schedule", backref="sidewalks")
