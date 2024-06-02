import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, User, Order, OrderStatus
import api

@pytest.fixture(scope='module')
def test_session():
    # Create a new database session for testing
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)

def test_register_user(test_session):
    # Test user registration
    api.register_user(test_session, "test_user", "test_pass")
    user = api.get_user(test_session, "test_user")
    assert user is not None
    assert user.login == "test_user"

def test_register_existing_user(test_session):
    # Test registering an existing user
    with pytest.raises(ValueError, match="User already exists"):
        api.register_user(test_session, "test_user", "test_pass")


def test_authenticate_user(test_session):
    # Test user authentication
    user = api.authenticate_user(test_session, "test_user", "test_pass")
    assert user is not None
    assert user.login == "test_user"

def test_authenticate_invalid_user(test_session):
    # Test invalid user authentication
    with pytest.raises(ValueError, match="Invalid login or password"):
        api.authenticate_user(test_session, "invalid_user", "test_pass")

def test_create_order(test_session):
    # Test creating an order
    user = api.get_user(test_session, "test_user")
    api.user_create_order(test_session, user, "origin", "destination", 100.0)
    orders = api.get_trip_history(test_session, user)
    assert len(orders) == 1
    assert orders[0].origin == "origin"
    assert orders[0].destination == "destination"


def test_get_trip_history(test_session):
    # Test retrieving trip history
    user = api.get_user(test_session, "test_user")
    orders = api.get_trip_history(test_session, user)
    assert len(orders) == 1


def test_rate_driver(test_session):
    # Test rating a driver
    user = api.get_user(test_session, "test_user")
    orders = api.get_trip_history(test_session, user)
    order_id = orders[0].id

    # Mark the order as completed
    order = test_session.query(Order).filter(Order.id == order_id).first()
    order.status = OrderStatus.COMPLETED
    test_session.commit()

    api.rate_driver(test_session, order_id, 4.5)
    order = api.get_order_details(test_session, order_id)
    assert order.driver_rating == 4.5


def test_cancel_order(test_session):
    # Test canceling an order
    user = api.get_user(test_session, "test_user")
    api.user_create_order(test_session, user, "origin2", "destination2", 150.0)
    orders = api.get_trip_history(test_session, user)
    order_id = orders[1].id
    api.cancel_order(test_session, order_id)
    order = api.get_order_details(test_session, order_id)
    assert order.status == OrderStatus.CANCELLED

def test_order_details(test_session):
    # Test retrieving order details
    user = api.get_user(test_session, "test_user")
    orders = api.get_trip_history(test_session, user)
    order_id = orders[0].id
    order = api.get_order_details(test_session, order_id)
    assert order is not None
    assert order.origin == "origin"
    assert order.destination == "destination"
    assert order.price == 100.0
