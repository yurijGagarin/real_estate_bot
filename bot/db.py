import datetime
from operator import or_
from typing import Dict, List, Type

from sqlalchemy import select, column, Column, delete, desc
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
    updated_date = datetime.datetime.utcnow()
    async with async_session() as session:
        for datum in data:
            instance = await session.get(model, datum['id'])
            if instance is None:
                instance = model(**datum)
                instance.updated_at = updated_date
            else:
                if is_data_new_for_instance(datum, instance):
                    for k, v in datum.items():
                        setattr(instance, k, v)
                    instance.created_at = updated_date
                instance.updated_at = updated_date
            session.add(instance)

        await session.commit()
        delete_stmt = delete(model).where(or_(model.updated_at < updated_date, model.updated_at.is_(None)))
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
        query = select(column_obj).distinct().select_from(source_query).filter(column_obj != '').order_by(column_obj)
        result = await session.execute(query)

        value = result.fetchall()
        return [v[0] for v in value]


async def get_result(source_query: Select, model: Type[bot.models.Ad]):
    async with async_session() as session:
        col_to_search = column('link')
        query = select(col_to_search).select_from(source_query).order_by(desc('created_at'))
        result = await session.execute(query)

        value = result.fetchall()
        print(value)
        return [v[0] for v in value]


async def get_user(update: Update):
    async with async_session() as session:
        user = await session.get(bot.models.User, update.effective_user.id)
        if not user:
            user = bot.models.User(
                id=update.effective_user.id,
                nickname=update.effective_user.username,
                last_active_at=datetime.datetime.utcnow()
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


async def get_users_with_subscription() -> List[bot.models.User]:
    async with async_session() as session:
        stmt = select(bot.models.User).where(bot.models.User.subscription != None)
        users = await session.execute(stmt)
        return [u[0] for u in users]


async def get_admin_users() -> List[bot.models.User]:
    async with async_session() as session:
        stmt = select(bot.models.User).where(bot.models.User.is_admin == True)
        result = await session.execute(stmt)
        users = result.fetchall()
        return [u[0] for u in users]


async def get_user_subscription(user: bot.models.User) -> List[str]:
    async with async_session() as session:
        serialized = user.subscription
        src_query = loads(serialized, bot.models.Base.metadata, session)
        table = src_query.froms[0]
        query = src_query \
            .filter(table.c.created_at > user.last_viewed_at) \
            .order_by(table.c.created_at) \
            .limit(3)

        result = await session.execute(query)

        rows = result.fetchall()
        links = []
        for row in rows:
            links.append(row[0].link)
        user.last_viewed_at = datetime.datetime.utcnow()
        await save_user(user)
        return links


async def get_regular_users():
    async with async_session() as session:
        result = await session.execute(select(bot.models.User).where(bot.models.User.is_admin != True))
        users = result.fetchall()

    return [u[0] for u in users]

