import asyncio
from functools import wraps
from pprint import pprint

import click

from bot.api.google import GoogleApi


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
@click.argument('name')
def get_sheet_data(name: str):
    api = GoogleApi()
    data = api.get_sheet_data(name)
    for datum in data:
        pprint(datum)


if __name__ == "__main__":
    cli()
