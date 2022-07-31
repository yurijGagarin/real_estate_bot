from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

import config

engine = create_async_engine(config.DB_URI)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

