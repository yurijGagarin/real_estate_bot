import datetime
from dataclasses import dataclass
from typing import Dict, List, Type, Optional

from sqlalchemy import or_, and_
from sqlalchemy import select, column, Column, delete, desc, Integer, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.serializer import loads
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import Select
from telegram import Update

import bot.models
from bot.config import DB_URI

engine = create_async_engine(DB_URI)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def remove_data_from_db(model_name):
    async with async_session() as session:
        await session.execute(model_name.__table__.delete())
        await session.commit()


def is_data_new_for_instance(data: Dict[str, str], instance: bot.models.Ad):
    for k, v in data.items():
        if v != getattr(instance, k):
            return True
    return False


async def sync_objects_to_db(model: Type[bot.models.Ad], data: List[Dict[str, str]]):
    # todo: it could be admin alert
    # seen = set()
    # not_uniq = []
    # for datum in data:
    #     if datum["id"] not in seen:
    #         seen.add(datum["id"])
    #     else:
    #         not_uniq.append(datum["id"])
    #
    # print(not_uniq)
    updated_date = datetime.datetime.utcnow()
    async with async_session() as session:
        max_id = (await session.execute(func.max(model.id))).scalar() or 0
        for datum in data:
            result = (await session.execute(select(model).where(model.link == datum["link"])))
            instances = result.fetchone()
            if instances is None:
                existing_row = await session.get(model, datum['id'])
                if existing_row is not None:
                    max_id += 1
                    datum['id'] = max_id
                else:
                    max_id = max(max_id, datum['id'])
                instance = model(**datum)
                instance.updated_at = updated_date
            else:
                instance = instances[0]
                del datum["id"]
                if is_data_new_for_instance(datum, instance):
                    for k, v in datum.items():
                        setattr(instance, k, v)
                    instance.created_at = updated_date
                instance.updated_at = updated_date
            session.add(instance)

        await session.commit()

        delete_stmt = delete(model).where(
            or_(model.updated_at < updated_date, model.updated_at.is_(None))
        )
        await session.execute(delete_stmt)
        await session.commit()
        print(delete_stmt)


async def get_model_by_link(model: Type[bot.models.Ad], link: str) -> bot.models.Ad:
    async with async_session() as session:
        stmt = select(model).where(model.link == link)
        result = await session.execute(stmt)
        instance = result.fetchone()
        return instance[0] if instance else None


async def delete_model_by_link(model: Type[bot.models.Ad], link: str):
    async with async_session() as session:
        delete_stmt = delete(model).where(model.link == link)
        await session.execute(delete_stmt)
        await session.commit()


async def get_unique_el_from_db(source_query: Select, col: Column):
    async with async_session() as session:
        column_obj = column(col.key)

        query = (
            select(column_obj).distinct().select_from(source_query).order_by(column_obj)
        )
        if not isinstance(col.type, Integer):
            query = query.filter(column_obj != " ")
        result = await session.execute(query)

        value = result.fetchall()
        return [v[0] for v in value]


async def get_result(source_query: Select, model: Type[bot.models.Ad]):
    async with async_session() as session:
        col_to_search = column("link")
        query = (
            select(col_to_search).select_from(source_query).order_by(desc("created_at"))
        )
        result = await session.execute(query)

        value = result.fetchall()
        # logging.debug(value)
        return [v[0] for v in value]

#todo get method to write data to geodata table
async def get_user(user_id: int):
    async with async_session() as session:
        user = await session.get(bot.models.User, user_id)

    return user



async def write_data_to_geodata_table(address: str, district: str, map_link: str, coordinates: Dict):
    async with async_session() as session:
        row = await session.get(bot.models.GeoData, (address, district))
        if not row:
            row = bot.models.GeoData(
                address=address,
                district=district,
                map_link=map_link,
                coordinates=coordinates,
            )
        else:
            row = row.update(address, district, map_link, coordinates)

        session.add(row)
        await session.commit()

    return row


async def get_user_or_create_new(update: Update):
    async with async_session() as session:
        user = await get_user(update.effective_user.id)
        if not user:
            user = bot.models.User(
                id=update.effective_user.id,
                nickname=update.effective_user.username,
                last_active_at=datetime.datetime.utcnow(),
            )
            session.add(user)
            await session.commit()
        else:
            user.last_active_at = datetime.datetime.utcnow()
            session.add(user)
            await session.commit()
    return user


async def save_user(user: bot.models.User):
    async with async_session() as session:
        session.add(user)
        await session.commit()
    return user


async def query_data(query):
    async with async_session() as session:
        result = await session.execute(query)
        users = result.fetchall()
        return [u[0] for u in users]


async def get_users_with_subscription() -> List[bot.models.User]:
    return await query_data(bot.models.User.get_user_with_subscription_query())


async def get_admin_users() -> List[bot.models.User]:
    return await query_data(bot.models.User.get_admin_query())


async def get_all_users():
    return await query_data(bot.models.User.get_regular_user_query())


async def get_recent_users(timedelta):
    return await query_data(bot.models.User.get_users_for_timedelta_query(timedelta))


async def get_user_subscription(user: bot.models.User) -> List[str]:
    async with async_session() as session:
        serialized = user.subscription
        src_query = loads(serialized, bot.models.Base.metadata, session)
        table = src_query.froms[0]
        query = (
            src_query.filter(table.c.created_at > user.last_viewed_at)
            .order_by(table.c.created_at)
            .limit(3)
        )

        result = await session.execute(query)

        rows = result.fetchall()
        links = []
        for row in rows:
            links.append(row[0].link)
        user.last_viewed_at = datetime.datetime.utcnow()
        await save_user(user)
        return links


async def migrate_data(new_db_uri):
    new_engine = create_async_engine(new_db_uri)

    async with engine.connect() as conn:
        async with new_engine.connect() as new_conn:
            for table in bot.models.Base.metadata.sorted_tables:
                data = [dict(row) for row in await conn.execute(select(table.c))]
                if len(data):
                    stmt = table.insert().values(data)
                    await new_conn.execute(stmt)
                    await new_conn.commit()


@dataclass
class AddressData:
    address: str
    district: str
    residential_complex: Optional[str] = None

    def to_text(self):
        parts = [
            self.address,
            self.district,
        ]
        if self.residential_complex is not None:
            parts.append(self.residential_complex)
        return '\n'.join(parts)

    def build_google_query_and_user_text(self):
        google_query = f'{self.address}, {self.district}, '
        text = f'Для обʼєкта за адресою:\nВулиця: {self.address}\nРайон: {self.district} '
        residential_complexes_to_exclude = ['всі інші жк', 'будинки 90х років', 'австрійський люкс', 'польський люкс']
        if self.residential_complex is not None:
            text += f'\nЖК: {self.residential_complex}'
            if self.residential_complex.lower() not in residential_complexes_to_exclude \
                    or self.residential_complex.lower() == self.address.lower():
                google_query += f'ЖК {self.residential_complex}, '
        google_query += f'Львів'
        
        return google_query, text


async def _get_address_without_link(model: Type[bot.models.Ad]) -> Optional[bot.models.Ad]:
    async with async_session() as session:
        condition = and_(or_(model.maps_link == None, model.maps_link == ''), bot.models.GeoData.address == None)
        stmt = select(model) \
            .join(bot.models.GeoData,
                  and_(bot.models.GeoData.address == model.address, bot.models.GeoData.district == model.district),
                  isouter=True) \
            .filter(condition) \
            .limit(1)
        r = await session.execute(stmt)

        instance = r.fetchone()
        return instance[0] if instance else None


async def get_address_without_link() -> Optional[AddressData]:
    a = await _get_address_without_link(bot.models.Apartments)
    if a is not None and isinstance(a, bot.models.Apartments):
        return AddressData(address=a.address, district=a.district, residential_complex=a.residential_complex)

    # h = await _get_address_without_link(bot.models.Houses)
    # if h is not None:
    #     return AddressData(address=h.address, district=h.district)

    return None
