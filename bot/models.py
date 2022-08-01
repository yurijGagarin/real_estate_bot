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
        return "<User(id='%s' name='%s', nickname='%s')>" % (
            self.id,
            self.name,
            self.nickname,
        )


class Apartments(Base):
    __tablename__ = "apartments"

    id = Column(Integer, primary_key=True)
    district = Column(String, nullable=False)
    street = Column(String, nullable=False)
    residential_complex = Column(String, nullable=False)
    rooms = Column(Integer, nullable=False)
    rent_price = Column(Integer, nullable=False)
    currency = Column(String, nullable=False)
    link = Column(String, nullable=False)

    def __repr__(self):
        return "<Apartments(id='%s' rent_price='%s', link='%s')>" % (
            self.id,
            self.rent_price,
            self.link,
        )