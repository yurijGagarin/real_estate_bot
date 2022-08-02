from typing import Dict, List, Type

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

import bot
from bot.config import DB_URI
from bot.models import Apartments

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
