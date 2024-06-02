from models import User, Order, OrderStatus, Tariff, PaymentMethod


def get_user(session, login: str) -> User:
    return session.query(User).filter(User.login == login).first()


def register_user(session, login: str, password: str):
    if get_user(session, login):
        raise ValueError("User already exists")
    new_user = User.create_user(login, password)
    session.add(new_user)
    session.commit()


def authenticate_user(session, login: str, password: str) -> User:
    user = get_user(session, login)
    if user and user.check_password(password):
        return user
    else:
        raise ValueError("Invalid login or password")


def user_create_order(session, user: User, origin: str, destination: str, price: float, tariff: Tariff, car: str,
                      plate_number: str, payment_method: PaymentMethod):
    new_order = Order.create_order(user.id, origin, destination, price, tariff, car, plate_number, payment_method)
    session.add(new_order)
    session.commit()


def get_trip_history(session, user: User):
    return session.query(Order).filter(Order.initiator_id == user.id).all()


def rate_driver(session, order_id: int, rating: float):
    order = session.query(Order).filter(Order.id == order_id).first()
    if order and order.status == OrderStatus.COMPLETED:
        order.driver_rating = rating
        session.commit()
    else:
        raise ValueError("Order not found or not completed")


def cancel_order(session, order_id: int):
    order = session.query(Order).filter(Order.id == order_id).first()
    if order:
        order.cancel()
        session.commit()
    else:
        raise ValueError("Order not found")


def get_order_details(session, order_id: int):
    return session.query(Order).filter(Order.id == order_id).first()
