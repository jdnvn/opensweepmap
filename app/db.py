from os import environ
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import AsyncAttrs, AsyncEngine, async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncAttrs, AsyncEngine, async_sessionmaker

DB_USER = "joey"
DB_PASSWORD = "sweep"
DB_HOST = "postgres"
DB_PORT = 5432
DB_NAME = "sweepmaps"

url = URL.create(
    drivername="postgresql+asyncpg",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME,
)

engine = create_async_engine(url, future=True)
Session = async_sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

async def get_session():
    async with Session() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()
