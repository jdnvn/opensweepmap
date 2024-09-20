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
from sqlalchemy import and_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import literal
from models import Sidewalk, Schedule


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
    tile_bounds_cte = select(
        ST_TileEnvelope(z, x, y).label("geom_3857"),
        ST_Transform(ST_TileEnvelope(z, x, y), 4326).label("geom_4326"),
    ).cte("tile_bounds_cte")

    mvt_table_cte = (
        select(
            ST_AsMVTGeom(
                ST_Transform(Sidewalk.geometry, 3857), tile_bounds_cte.c.geom_3857
            ).label("geom"),
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
        .select_from(Sidewalk)
        .join(tile_bounds_cte, literal(True))
        .join(Schedule, Sidewalk.schedule_id == Schedule.id)
        .filter(
            ST_Intersects(Sidewalk.geometry, tile_bounds_cte.c.geom_4326)
        )
    )

    mvt_table_cte = mvt_table_cte.cte("mvt_table_cte")
    stmt = select(ST_AsMVT(text("mvt_table_cte.*"), 'default', 4096, 'geom', 'id')).select_from(mvt_table_cte)
    result = await session.execute(stmt)
    return result.scalar()


@cached(
    ttl=600,
    cache=Cache.MEMORY,
    serializer=PickleSerializer(),
)
async def get_sidewalk_by_id(
    id: str,
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
        .where(Sidewalk.id == int(id))
    )

    result = await session.execute(query)

    sidewalk = result.first()
    if sidewalk is None:
        return None

    return sidewalk._asdict()
