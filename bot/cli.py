import asyncio
from functools import wraps
from pprint import pprint

import click

import bot.models
from bot.api.google import GoogleApi
from bot.data_manager import DataManager
from bot.db import (
    async_session,
    get_all_users,
    get_users_with_subscription,
    get_admin_users,
    migrate_data as migrate_data_internal,
)
from bot.notifications import send_message_to_users


@click.group()
def cli():
    pass


def coro(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return wrapper


@cli.command()
def gen_google_token():
    api = GoogleApi()
    api.generate_creds()


@cli.command()
@click.argument("name")
def get_sheet_data(name: str):
    api = GoogleApi()
    data = api.get_sheet_data(name)
    for datum in data:
        pprint(datum)


@cli.command()
@coro
async def sync_data():
    data_manager = DataManager()
    await data_manager.sync_data()


@cli.command()
@coro
async def get_admins():
    users = await get_admin_users()
    for user in users:
        print(user.id, user)


@cli.command()
@click.argument("user_id", type=click.INT)
@coro
async def user_to_admin(user_id):
    async with async_session() as session:
        user = await session.get(bot.models.User, user_id)
        if user and not user.is_admin:
            user.is_admin = True
            session.add(user)
        await session.commit()


@cli.command()
@coro
async def get_number_of_users():
    users = await get_all_users()
    print("Total users:", len(users))
    for user in users:
        print(user.id, user)


@cli.command()
@coro
async def get_number_of_users_with_subscription():
    users = await get_users_with_subscription()
    print("Total users:", len(users))
    for user in users:
        print(
            user.id,
            user.subscription_text,
            user,
        )


@cli.command()
@click.argument("db_uri", type=click.STRING)
@coro
async def migrate_data(db_uri):
    await migrate_data_internal(db_uri)
    print("migrated")


if __name__ == "__main__":
    cli()
