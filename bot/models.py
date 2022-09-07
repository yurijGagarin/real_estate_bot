import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean, DateTime, Text, select, BigInteger, LargeBinary, )
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True)
    is_admin = Column(Boolean, default=False)
    nickname = Column(String)
    last_viewed_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_active_at = Column(DateTime, default=datetime.datetime.utcnow)
    subscription = Column(LargeBinary, nullable=True)
    subscription_text = Column(Text, nullable=True)

    def __repr__(self):
        return "<User(id='%s', nickname='%s')>" % (
            self.id,
            self.nickname,
        )

    @classmethod
    def get_admin_query(cls):
        return select(cls).where(cls.is_admin == True)

    @classmethod
    def get_regular_user_query(cls):
        return select(cls).where(cls.is_admin != True)

    @classmethod
    def get_users_for_timedelta_query(cls, timedelta):
        return select(cls).where(cls.last_active_at >= timedelta)

    @classmethod
    def get_user_with_subscription_query(cls):
        return select(cls).where(cls.subscription != None)


class Ad(Base):
    __abstract__ = True
    id = Column(BigInteger, primary_key=True)
    rent_price = Column(Integer, nullable=False)
    currency = Column(String, nullable=False)
    link = Column(String, nullable=False)
    rooms = Column(Integer, nullable=False)
    district = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.datetime.utcnow)

    def get_full_name(self):
        return f"ID: {self.id} Link: {self.link}"


class Apartments(Ad):
    __tablename__ = "apartments"

    street = Column(String, nullable=False)
    residential_complex = Column(String, nullable=False)
    kids = Column(String, nullable=True)
    pets = Column(String, nullable=True)

    def __repr__(self):
        return "<Apartments(id='%s' rent_price='%s', link='%s')>" % (
            self.id,
            self.rent_price,
            self.link,
        )


class Houses(Ad):
    __tablename__ = "houses"

    placing = Column(String, nullable=False)
    living_area = Column(Integer, nullable=False)
    territory_area = Column(Integer, nullable=False)

    def __repr__(self):
        return "<Apartments(id='%s', living_area='%s' rent_price='%s', link='%s')>" % (
            self.id,
            self.rent_price,
            self.living_area,
            self.link,
        )
