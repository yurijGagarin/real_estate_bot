from typing import Dict, List, Type

from sqlalchemy import select, column
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import Select

import bot.models
from bot.config import DB_URI

engine = create_async_engine(DB_URI)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def remove_data_from_db(model_name):
    async with async_session() as session:
        await session.execute(model_name.__table__.delete())
        await session.commit()


async def add_objects_to_db(db: Type[bot.models.Ad], data: List[Dict[str, str]]):
    async with async_session() as session:
        for datum in data:
            obj = db(**datum)
            session.add(obj)
        await session.commit()


async def get_unique_el_from_db(source_query: Select, col: str):
    async with async_session() as session:
        col_to_search = column(col)
        query = select(col_to_search).distinct().select_from(source_query)
        result = await session.execute(query)

        value = result.fetchall()
        return [v[0] for v in value]


async def get_result(source_query: Select):
    async with async_session() as session:
        col_to_search = column('link')
        query = select(col_to_search).select_from(source_query)
        result = await session.execute(query)

        value = result.fetchall()
        print(value)
        return [v[0] for v in value]
