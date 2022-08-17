from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    is_admin = Column(Boolean, default=False)
    nickname = Column(String)

    def __repr__(self):
        return "<User(id='%s', nickname='%s')>" % (
            self.id,
            self.nickname,
        )


class Ad(Base):
    __abstract__ = True
    id = Column(Integer, primary_key=True)
    rent_price = Column(Integer, nullable=False)
    currency = Column(String, nullable=False)
    link = Column(String, nullable=False)
    rooms = Column(Integer, nullable=False)
    district = Column(String, nullable=False)


class Apartments(Ad):
    __tablename__ = "apartments"

    street = Column(String, nullable=False)
    residential_complex = Column(String, nullable=False)

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


