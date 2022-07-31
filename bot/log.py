import logging

from bot import config

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.DEBUG if config.DEBUG else logging.INFO,
)
