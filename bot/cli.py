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
    migrate_data as migrate_data_internal, get_address_with_coordinates,
)
from bot.proxies import get_proxies
from bot.stages.admin_stage import write_coordinates_to_db_from_gmaps_link


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
@click.argument("name")
@click.argument("address")
@click.argument("district")
def get_sheet_data_to_insert(name: str, address: str, district: str):
    api = GoogleApi()
    data = api.get_sheet_data(name)
    to_insert = []
    for i, row in enumerate(data[1:], 2):
        if address in row and district in row:
            to_insert.append(i)
    return to_insert


@cli.command()
@click.argument("name")
@click.argument("address")
@click.argument("district")
def insert_data_to_spreadsheet(name: str, address: str, district: str):
    api = GoogleApi()
    data = api.get_sheet_data(name)
    idxs = []
    for i, row in enumerate(data):
        if address in row and district in row:
            idxs.append(i)
    # idxs = [1,2,3]
    link = 'https://maps.google.com/?q=%D0%9B%D1%8C%D0%B2%D1%96%D0%B2%D1%81%D1%8C%D0%BA%D0%B0+33%D0%B0%2C+%D0%91%D1%80%D1%8E%D1%85%D0%BE%D0%B2%D0%B8%D1%87%D1%96%2C+%D0%96%D0%9A+%D0%A5%D0%B2%D0%B8%D0%BB%D1%8F%2C+%D0%9B%D1%8C%D0%B2%D1%96%D0%B2'
    data = api.batch_update_google_maps_link_by_row_idx(idxs, link)
    print(data)
    return data


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
@coro
async def write_coordinates():
   r= await get_address_with_coordinates(bot.models.Apartments)
   pprint(r)
   print(len(r))



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
