from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from passlib.hash import bcrypt
from sqlalchemy.orm import relationship
from sqlalchemy.orm import RelationshipProperty
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    login = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    orders = relationship("Order", back_populates="initiator")

    def set_password(self, password):
        # Validate and set the password hash using bcrypt
        self.password_hash = bcrypt.hash(password)

    def check_password(self, password):
        # Verify the provided password against the stored hash
        return bcrypt.verify(password, self.password_hash)

    @classmethod
    def create_user(cls, login, password):
        # Create and return a new User instance with hashed password
        pass_hash = bcrypt.hash(password)
        return cls(login=login, password_hash=pass_hash)

    def __repr__(self):
        return f'User(id={self.id}, login={self.login})'


class Order(Base):
    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True)
    initiator_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    initiator = relationship('User', back_populates='orders')

    @classmethod
    def create_order(cls, initiator_id):
        return cls(initiator_id=initiator_id)

    def __repr__(self):
        return f'Order(id={self.id}, initiator_id={self.initiator_id})'
    # TODO: точка отправления, точка назначния, цена, статус (отменен, ..., в ожидании клиента, в исполнении)


