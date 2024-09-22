import os
import gzip
from models import Sidewalk, Schedule
from datetime import datetime, timedelta
from fastapi import Depends, FastAPI, Path, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, select, text, update
from queries import get_sidewalks_tiles_bytes, get_sidewalk_by_id
from db import get_session

SERVER_PORT = os.environ.get('SERVER_PORT', 8000)
SERVER_HOST = os.environ.get('SERVER_HOST')
SERVER_URL = SERVER_HOST if SERVER_HOST else f"http://127.0.0.1:{SERVER_PORT}"

app = FastAPI()
templates = Jinja2Templates(directory="./templates")

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
