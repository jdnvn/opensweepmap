from typing import Dict
from aiocache import Cache, cached
from aiocache.serializers import PickleSerializer
from geoalchemy2.functions import (
    ST_AsMVT,
    ST_AsMVTGeom,
    ST_Intersects,
    ST_TileEnvelope,
    ST_Transform,
)
from sqlalchemy import and_, select, text, update, func, case, DateTime, cast
from sqlalchemy.types import TIMESTAMP
from sqlalchemy.ext.asyncio import AsyncSession
from models import Sidewalk, Schedule, User, SidewalkAdjustment
from datetime import datetime, timedelta

@cached(
    ttl=600,
    cache=Cache.MEMORY,
    serializer=PickleSerializer(),
)
async def get_sidewalks_tiles_bytes(
    session: AsyncSession,
    z: int,
    x: int,
    y: int,
) -> bytes | None:
    query = text("""
    WITH RECURSIVE next_sweep_day AS (
        SELECT
            CURRENT_DATE::timestamp AS day
        UNION ALL
        SELECT
            day + INTERVAL '1 day'
        FROM next_sweep_day
        WHERE day < CURRENT_DATE::timestamp + INTERVAL '60 days' -- Max lookahead of 6 weeks
    ),
    next_sweep_schedule AS (
        SELECT
            s.id,
            s.start_time,
            s.end_time,
            CASE
                WHEN s.every_day THEN TRUE
                WHEN EXTRACT(DOW FROM nsd.day) = 0 AND s.sunday THEN TRUE
                WHEN EXTRACT(DOW FROM nsd.day) = 1 AND s.monday THEN TRUE
                WHEN EXTRACT(DOW FROM nsd.day) = 2 AND s.tuesday THEN TRUE
                WHEN EXTRACT(DOW FROM nsd.day) = 3 AND s.wednesday THEN TRUE
                WHEN EXTRACT(DOW FROM nsd.day) = 4 AND s.thursday THEN TRUE
                WHEN EXTRACT(DOW FROM nsd.day) = 5 AND s.friday THEN TRUE
                WHEN EXTRACT(DOW FROM nsd.day) = 6 AND s.saturday THEN TRUE
                ELSE FALSE
            END AS valid_day,
            CASE
                WHEN s.every_day THEN TRUE
                WHEN to_char(nsd.day, 'W')::integer = 1 AND s.week_1 THEN TRUE
                WHEN to_char(nsd.day, 'W')::integer = 2 AND s.week_2 THEN TRUE
                WHEN to_char(nsd.day, 'W')::integer = 3 AND s.week_3 THEN TRUE
                WHEN to_char(nsd.day, 'W')::integer = 4 AND s.week_4 THEN TRUE
                WHEN to_char(nsd.day, 'W')::integer = 5 AND s.week_5 THEN TRUE
                ELSE FALSE
            END AS valid_week,
            nsd.day
        FROM
            schedules s
        CROSS JOIN
            next_sweep_day nsd
        WHERE
            (nsd.day > CURRENT_DATE::timestamp
            OR (s.start_time::time > CURRENT_TIME))
    ),
    next_sweep_times AS (
        SELECT DISTINCT ON (s.id)
            s.id,
            nsd.day::date AS next_sweep_at
        FROM
            next_sweep_schedule nsd
        JOIN
            schedules s ON s.id = nsd.id
        WHERE
            nsd.valid_day = TRUE
            AND nsd.valid_week = TRUE
        ORDER BY
            s.id,
            nsd.day ASC
    ),
    tile_bounds_cte AS (
        SELECT
            ST_TileEnvelope(:z, :x, :y) AS geom_3857,
            ST_Transform(ST_TileEnvelope(:z, :x, :y), 4326) AS geom_4326
    ),
    mvt_table_cte AS (
        SELECT
            ST_AsMVTGeom(
                ST_Transform(sidewalks.geometry, 3857), 
                tile_bounds_cte.geom_3857
            ) AS geom,
            sidewalks.id,
            sidewalks.schedule_id,
            sidewalks.status,
            schedules.street_name,
            schedules.suburb_name,
            schedules.side,
            schedules.start_time,
            schedules.end_time,
            schedules.from_street_name,
            schedules.to_street_name,
            schedules.has_duplicates,
            schedules.one_way,
            schedules.week_1,
            schedules.week_2,
            schedules.week_3,
            schedules.week_4,
            schedules.week_5,
            schedules.sunday,
            schedules.monday,
            schedules.tuesday,
            schedules.wednesday,
            schedules.thursday,
            schedules.friday,
            schedules.saturday,
            schedules.every_day,
            schedules.year_round,
            schedules.north_end_pilot,
            next_sweep_times.next_sweep_at,
            FLOOR((EXTRACT(EPOCH FROM next_sweep_times.next_sweep_at + schedules.start_time::interval) - EXTRACT(EPOCH FROM CURRENT_DATE::timestamp))/3600) as hours_to_next_sweep
        FROM
            sidewalks
        JOIN
            tile_bounds_cte ON TRUE
        LEFT JOIN
            schedules ON sidewalks.schedule_id = schedules.id
        LEFT JOIN
            next_sweep_times ON schedules.id = next_sweep_times.id
        WHERE
            ST_Intersects(sidewalks.geometry, tile_bounds_cte.geom_4326)
    )
    SELECT 
        ST_AsMVT(mvt_table_cte.*, 'default', 4096, 'geom', 'id') 
    FROM 
        mvt_table_cte;
    """)

    result = await session.execute(query, {"z": z, "x": x, "y": y})
    return result.scalar()


@cached(
    ttl=600,
    cache=Cache.MEMORY,
    serializer=PickleSerializer(),
)
async def get_sidewalk_by_id(
    id: int,
    session: AsyncSession
) -> Dict:
    query = (
        select(
            Sidewalk.id,
            Sidewalk.schedule_id,
            Sidewalk.status,
            Schedule.street_name,
            Schedule.suburb_name,
            Schedule.side,
            Schedule.start_time,
            Schedule.end_time,
            Schedule.from_street_name,
            Schedule.to_street_name,
            Schedule.has_duplicates,
            Schedule.one_way,
            Schedule.week_1,
            Schedule.week_2,
            Schedule.week_3,
            Schedule.week_4,
            Schedule.week_5,
            Schedule.sunday,
            Schedule.monday,
            Schedule.tuesday,
            Schedule.wednesday,
            Schedule.thursday,
            Schedule.friday,
            Schedule.saturday,
            Schedule.every_day,
            Schedule.year_round,
            Schedule.north_end_pilot
        )
        .outerjoin(Schedule, Sidewalk.schedule_id == Schedule.id)
        .where(Sidewalk.id == id)
    )

    result = await session.execute(query)

    sidewalk = result.first()
    if sidewalk is None:
        return None

    return sidewalk._asdict()


async def get_user(username: str, session: AsyncSession, email: str | None = None) -> Dict:
    if email:
        query = select(User).filter((User.username == username) | (User.email == email))
    else:
        query = select(User).filter(User.username == username)
    result = await session.execute(query)
    user = result.scalars().first()
    if user is None:
        return None
    return user


async def create_user(username: str, email: str, hashed_password: str, session: AsyncSession) -> Dict:
    new_user = User(
        username=username,
        email=email,
        hashed_password=hashed_password,
        role="adjuster"
    )

    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)

    return new_user


async def create_sidewalk_adjustment(sidewalk_id: int, schedule_id: int, status: str, user_id: int, session: AsyncSession) -> Dict:
    new_adjustment = SidewalkAdjustment(
        user_id=user_id,
        sidewalk_id=sidewalk_id,
        schedule_id=schedule_id,
        status=status
    )

    session.add(new_adjustment)
    await session.commit()
    await session.refresh(new_adjustment)

    return new_adjustment
