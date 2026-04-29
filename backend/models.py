from sqlalchemy import Column, Integer, String
from db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, index=True) # Unique per app, not globally
    password = Column(String)
    role = Column(String, default="user")
    app_id = Column(String, index=True, default="default")
