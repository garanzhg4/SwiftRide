from sqlalchemy import Column, Integer, String, ForeignKey, Float, Enum, DateTime, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from passlib.hash import bcrypt
from sqlalchemy.orm import relationship
import enum
from datetime import datetime
from cryptography.fernet import Fernet

Base = declarative_base()

key = Fernet.generate_key()
cipher_suite = Fernet(key)


class Tariff(enum.Enum):
    ECONOMY = "economy"
    COMFORT = "comfort"
    BUSINESS = "business"


class OrderStatus(enum.Enum):
    CANCELLED = "cancelled"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class PaymentMethod(enum.Enum):
    CASH = "cash"
    CARD = "card"


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    login = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    card_number = Column(LargeBinary, nullable=True)
    card_expiry_date = Column(LargeBinary, nullable=True)
    card_cvv = Column(LargeBinary, nullable=True)
    orders = relationship("Order", back_populates="initiator")

    def set_password(self, password):
        self.password_hash = bcrypt.hash(password)

    def check_password(self, password):
        return bcrypt.verify(password, self.password_hash)

    def set_card_info(self, card_number, card_expiry_date, card_cvv):
        self.card_number = cipher_suite.encrypt(card_number.encode())
        self.card_expiry_date = cipher_suite.encrypt(card_expiry_date.encode())
        self.card_cvv = cipher_suite.encrypt(card_cvv.encode())

    def get_card_info(self):
        return {
            "card_number": cipher_suite.decrypt(self.card_number).decode() if self.card_number else None,
            "card_expiry_date": cipher_suite.decrypt(self.card_expiry_date).decode() if self.card_expiry_date else None,
            "card_cvv": cipher_suite.decrypt(self.card_cvv).decode() if self.card_cvv else None,
        }

    def get_last_four_digits(self):
        card_info = self.get_card_info()
        if card_info['card_number']:
            return card_info['card_number'][-4:]
        return None

    @classmethod
    def create_user(cls, login, password):
        pass_hash = bcrypt.hash(password)
        return cls(login=login, password_hash=pass_hash)

    def __repr__(self):
        return f'User(id={self.id}, login={self.login})'


class Order(Base):
    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True)
    initiator_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    initiator = relationship('User', back_populates='orders')
    origin = Column(String(100))
    destination = Column(String(100))
    price = Column(Float)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    driver_rating = Column(Float, nullable=True)
    tariff = Column(Enum(Tariff), nullable=False)
    car = Column(String(50), nullable=False)
    plate_number = Column(String(10), nullable=False)
    payment_method = Column(Enum(PaymentMethod), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    @classmethod
    def create_order(cls, initiator_id, origin, destination, price, tariff, car, plate_number, payment_method):
        return cls(initiator_id=initiator_id, origin=origin, destination=destination, price=price, tariff=tariff, car=car, plate_number=plate_number, payment_method=payment_method)

    def cancel(self):
        if self.status == OrderStatus.PENDING:
            self.status = OrderStatus.CANCELLED
        else:
            raise ValueError("Order cannot be cancelled")

    def __repr__(self):
        return (f'Order(id={self.id}, initiator_id={self.initiator_id}, origin={self.origin}, '
                f'destination={self.destination}, price={self.price}, status={self.status}, '
                f'driver_rating={self.driver_rating}, created_at={self.created_at}, tariff={self.tariff}, '
                f'car={self.car}, plate_number={self.plate_number}, payment_method={self.payment_method})')
