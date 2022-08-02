from typing import Dict

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from bot.config import DB_URI
from bot.models import Apartments, Houses

engine = create_async_engine(DB_URI)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def remove_data_from_db(model_name):
    async with async_session() as session:
        await session.execute(model_name.__table__.delete())
        await session.commit()


# async def add_objects_from_mapping_to_db(db: bot.models, mapped_data: Dict):
#     async with async_session() as session:
#         obj = db(
#             id=mapped_data["id"],
#             district=mapped_data["district"],
#             street=mapped_data["street"],
#             residential_complex=mapped_data["residential_complex"],
#             rooms=mapped_data["rooms"],
#             rent_price=mapped_data["rent_price"],
#             currency=mapped_data["currency"],
#             link=mapped_data["link"],
#         )
#         session.add(obj)
#         await session.commit()

async def add_objects_to_apartments_db(mapped_data: Dict):
    async with async_session() as session:
        obj = Apartments(
            id=mapped_data["id"],
            district=mapped_data["district"],
            street=mapped_data["street"],
            residential_complex=mapped_data["residential_complex"],
            rooms=mapped_data["rooms"],
            rent_price=mapped_data["rent_price"],
            currency=mapped_data["currency"],
            link=mapped_data["link"],
        )
        session.add(obj)
        await session.commit()


async def add_objects_to_houses_db(mapped_data: Dict):
    async with async_session() as session:
        obj = Houses(
            id=mapped_data["id"],
            district=mapped_data["district"],
            placing=mapped_data["placing"],
            living_area=mapped_data["living_area"],
            territory_area=mapped_data["territory_area"],
            rooms=mapped_data["rooms"],
            rent_price=mapped_data["rent_price"],
            currency=mapped_data["currency"],
            link=mapped_data["link"],
        )
        session.add(obj)
        await session.commit()
