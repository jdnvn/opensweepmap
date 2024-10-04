import os
import gzip
import logging
from models import Sidewalk, Schedule, User
from datetime import datetime, timedelta
from fastapi import Depends, FastAPI, Path, Request, Response, status, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from fastapi.logger import logger as fastapi_logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, select, text, update
from queries import get_sidewalks_tiles_bytes, get_sidewalk_by_id, get_user, create_user, create_sidewalk_adjustment
from db import get_session
from auth import create_access_token, verify_password, get_password_hash, verify_access_token

SERVER_PORT = os.environ.get('SERVER_PORT', 8000)
SERVER_HOST = os.environ.get('SERVER_HOST')
SERVER_URL = SERVER_HOST if SERVER_HOST else f"http://127.0.0.1:{SERVER_PORT}"

app = FastAPI()
templates = Jinja2Templates(directory="./templates")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
logger = logging.getLogger("gunicorn.error")
fastapi_logger.handlers = logger.handlers
fastapi_logger.setLevel(logger.level)


async def get_current_user(token: str = Depends(oauth2_scheme), session: AsyncSession = Depends(get_session)):
    current_username = verify_access_token(token)
    user = await get_user(username=current_username, session=session)
    return user


@app.get("/", response_class=HTMLResponse)
async def map(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="map.html",
        context={
            "server_url": SERVER_URL
        },
    )


@app.post("/login")
async def login(request: dict, session: AsyncSession = Depends(get_session)):
    try:
        username = request.get('username')
        password = request.get('password')
    except:
        return JSONResponse(status_code=422, content={'message': 'invalid request body'})

    user = await get_user(username=username, session=session)
    if not user or not verify_password(password, user.hashed_password):
        return JSONResponse(status_code=401, content={'data': 'invalid username or password'})

    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/register")
async def register(request: dict, session: AsyncSession = Depends(get_session)):
    try:
        username = request.get("username")
        email = request.get("email")
        password = request.get("password")
    except:
        return JSONResponse(status_code=422, content={'message': 'invalid request body'})

    existing_user = await get_user(username=username, email=email, session=session)
    if existing_user:
        return JSONResponse(status_code=400, content={'data': 'user already exists with those credentials'})

    hashed_password = get_password_hash(password)

    new_user = await create_user(
        username=username,
        email=email,
        hashed_password=hashed_password,
        session=session
    )

    return JSONResponse(status_code=201, content={'data': new_user.as_dict()})


@app.get('/me')
def me(current_user: User = Depends(get_current_user)):
    return JSONResponse(status_code=200, content={'data': current_user.as_dict()})


async def tile_args(
    z: int = Path(..., ge=0, le=24),
    x: int = Path(..., ge=0),
    y: int = Path(..., ge=0),
) -> dict[str, str]:
    return dict(z=z, x=x, y=y)

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
async def put_sidewalk(id: int, request: dict, session: AsyncSession = Depends(get_session), current_user: User = Depends(get_current_user)):
    logger.info("PUT /sidewalks/{id}")
    sidewalk = await get_sidewalk_by_id(id, session)
    if sidewalk is None:
        return JSONResponse(status_code=404, content={'message': 'not found'})

    try:
        # Parse incoming JSON request
        schedule_id = int(request.get("schedule_id"))
        status = request.get("status")

        logger.info(f"Incoming PUT request for sidewalk id: {id}")
        logger.info(request)
    except Exception as e:
        logger.info(f"ERROR: {str(e)}")
        return JSONResponse(status_code=422, content={'message': 'invalid request body'})

    if int(sidewalk['schedule_id']) != schedule_id:
        status = 'ok'

    try:
        stmt = (
            update(Sidewalk)
            .where(Sidewalk.id == id)
            .values(schedule_id=schedule_id, status=status)
        )

        new_adjustment = await create_sidewalk_adjustment(
            sidewalk_id=id,
            schedule_id=schedule_id,
            status=status,
            user_id=current_user.id,
            session=session
        )

        await session.execute(stmt)
        await session.commit()

        updated_sidewalk = await get_sidewalk_by_id(id, session)
    except Exception as e:
        logger.info(f"ERROR: {str(e)}")
        return JSONResponse(status_code=500, content={'message': 'something went wrong'})

    return JSONResponse(status_code=200, content={'data': updated_sidewalk})
