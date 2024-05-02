from models import User, Base, Order
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import api

engine = create_engine('sqlite:///users.db', echo=True)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()


orders = session.query(Order).all()
api.user_create_order(session, "test", "testpass")
user = api.get_user(session, "test")
print(orders)
# new_user = User.create_user("test", "testpass")
# print("success")
