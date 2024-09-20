import os
from models import Sidewalk, Schedule
from datetime import datetime, timedelta

import gzip

from fastapi import Depends, FastAPI, Path, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, select, text, update
templates = Jinja2Templates(directory="./templates")
from queries import get_sidewalks_tiles_bytes, get_sidewalk_by_id
from db import get_session

SERVER_PORT = os.environ.get('SERVER_PORT', 8000)
SERVER_HOST = os.environ.get('SERVER_HOST')
SERVER_URL = SERVER_HOST if SERVER_HOST else f"http://127.0.0.1:{SERVER_PORT}"

app = FastAPI()

async def tile_args(
    z: int = Path(..., ge=0, le=24),
    x: int = Path(..., ge=0),
    y: int = Path(..., ge=0),
) -> dict[str, str]:
    return dict(z=z, x=x, y=y)


@app.get("/", response_class=HTMLResponse)
async def map(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="map.html",
        context={
            "server_url": SERVER_URL
        },
    )


@app.get(
    "/sidewalks/tiles/{z}/{x}/{y}.mvt",
    summary="Get sidewalkTiles",
)
async def get_sidewalk_tiles(
    tile: dict[str, int] = Depends(tile_args),
    session: AsyncSession = Depends(get_session),
) -> Response:
    byte_tile = await get_sidewalks_tiles_bytes(
        session=session, **tile
    )
    byte_tile = b"" if byte_tile is None else byte_tile
    return Response(
        content=gzip.compress(byte_tile),
        media_type="application/vnd.mapbox-vector-tile",
        headers={"Content-Encoding": "gzip"},
        status_code=status.HTTP_200_OK,
    )

@app.put('/sidewalks/{id}')
async def put_sidewalk(id: str, request: Request, session: AsyncSession = Depends(get_session)):
    sidewalk = await get_sidewalk_by_id(id, session)
    if sidewalk is None:
        return JSONResponse(status_code=404, content={'message': 'not found'})

    try:
        # Parse incoming JSON request
        content = await request.json()
        schedule_id = content["schedule_id"]
        status = content["status"]
        
        print(f"Incoming PUT request for sidewalk id: {id}")
        print(content)
    except Exception as e:
        print(f"ERROR: {str(e)}")
        raise JSONResponse(status_code=422, content={'message': 'invalid request body'})

    if sidewalk['schedule_id'] != int(schedule_id):
        status = 'ok'

    try:
        stmt = (
            update(Sidewalk)
            .where(Sidewalk.id == int(id))
            .values(schedule_id=int(schedule_id), status=status)
        )

        await session.execute(stmt)
        await session.commit()

        updated_sidewalk = await get_sidewalk_by_id(id, session)
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        raise JSONResponse(status_code=500, content={'message': 'something went wrong'})

    return JSONResponse(status_code=201, content={'data': updated_sidewalk})


@app.route('/sidewalks/<id>', methods=['PUT'])
def put_sidewalk(id):
    sidewalks = get_sidewalks_data(ids=[id])
    if not sidewalks:
        return jsonify({'message': 'not found'}), 404

    sidewalk = sidewalks[0]

    try:
        content = request.get_json()
        print("incoming PUT request for sidewalk id: ", id)
        print(content)
        schedule_id = content["schedule_id"]
        status = content["status"]
    except Exception as e:
        print("ERROR: {e}")
        return jsonify({'error': str(e), 'message': 'Invalid request body'}), 422

    if sidewalk['schedule_id'] != int(schedule_id):
        status = 'ok'

    try:
        with Session() as session:
            stmt = (
                update(Sidewalk).
                where(Sidewalk.id == id).
                values(schedule_id=schedule_id, status=status)
            )

            session.execute(stmt)
            session.commit()

        updated_sidewalk = get_sidewalks_data(ids=[id])[0]
    except Exception as e:
        print("ERROR: {e}")
        return jsonify({'error': str(e), 'message': 'Something went wrong'}), 500

    print(f"updated sidewalk: {updated_sidewalk}")

    return jsonify(updated_sidewalk)


# @app.route('/')
# def map_view():
#     return render_template('map.html', server_url=SERVER_URL)




# def get_next_sweeping_date(schedule):
#     # Define days of the week mapping
#     days_of_week = {
#         'sunday': 6,
#         'monday': 0,
#         'tuesday': 1,
#         'wednesday': 2,
#         'thursday': 3,
#         'friday': 4,
#         'saturday': 5
#     }

#     today = datetime.now().weekday()
#     days = {
#         'monday': schedule.get('monday', False),
#         'tuesday': schedule.get('tuesday', False),
#         'wednesday': schedule.get('wednesday', False),
#         'thursday': schedule.get('thursday', False),
#         'friday': schedule.get('friday', False),
#         'saturday': schedule.get('saturday', False),
#         'sunday': schedule.get('sunday', False)
#     }

#     # Check if sweeping is every day
#     if schedule.get('every_day', False):
#         next_sweep_date = datetime.now() + timedelta(days=1)
#         return next_sweep_date.strftime('%Y-%m-%d')

#     # Find the next sweeping day
#     for i in range(1, 8):  # Check up to a week ahead
#         next_date = datetime.now() + timedelta(days=i)
#         next_weekday = next_date.weekday()
#         if days.get(next_weekday, False):
#             return next_date.strftime('%Y-%m-%d')

#     return None


# def get_sidewalks_data(ids=[], as_json=True, session=None):
#     with Session() as session:
#         sidewalks_query = session.query(
#             Sidewalk.id,
#             Sidewalk.schedule_id,
#             Sidewalk.status,
#             func.ST_AsGeoJSON(Sidewalk.geometry).label('geojson'),
#             Schedule.street_name,
#             Schedule.suburb_name,
#             Schedule.side,
#             Schedule.start_time,
#             Schedule.end_time,
#             Schedule.from_street_name,
#             Schedule.to_street_name,
#             Schedule.has_duplicates,
#             Schedule.one_way,
#             Schedule.week_1,
#             Schedule.week_2,
#             Schedule.week_3,
#             Schedule.week_4,
#             Schedule.week_5,
#             Schedule.sunday,
#             Schedule.monday,
#             Schedule.tuesday,
#             Schedule.wednesday,
#             Schedule.thursday,
#             Schedule.friday,
#             Schedule.saturday,
#             Schedule.every_day,
#             Schedule.year_round,
#             Schedule.north_end_pilot
#         ).outerjoin(Schedule, Sidewalk.schedule_id == Schedule.id)

#         if ids:
#             sidewalks_query = sidewalks_query.filter(Sidewalk.id.in_(ids))

#         sidewalks_data = sidewalks_query.all()
#         if as_json:
#             sidewalks_data = [row._asdict() for row in sidewalks_data]

#     return sidewalks_data


# @app.route('/sidewalks', methods=['GET'])
# def get_sidewalks():
#     try:
#         sidewalks = get_sidewalks_data()
#         sidewalks = [{**sidewalk, "next_sweep": get_next_sweeping_date(sidewalk)} for sidewalk in sidewalks]

#         return jsonify({"data": sidewalks})
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500




# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=SERVER_PORT, debug=True)
