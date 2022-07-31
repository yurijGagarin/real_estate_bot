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
