import argparse
import logging
import math
import os
import time
import random
import string
import inquirer
from ymaps import Geocode
from models import Base, Order, OrderStatus, Tariff, PaymentMethod
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import api

logging.getLogger('passlib').setLevel(logging.ERROR)
engine = create_engine('sqlite:///users.db', echo=False)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

YANDEX_API_KEY = os.getenv('YANDEX_API_KEY')
y_geocode = Geocode(api_key=YANDEX_API_KEY)

TARIFF_MULTIPLIERS = {
    Tariff.ECONOMY: 1.0,
    Tariff.COMFORT: 1.5,
    Tariff.BUSINESS: 2.0
}

CARS = {
    Tariff.ECONOMY: ["Hyundai Solaris", "Kia Rio", "Renault Logan"],
    Tariff.COMFORT: ["Toyota Camry", "Honda Accord", "Mazda 6"],
    Tariff.BUSINESS: ["Mercedes E-Class", "BMW 5 Series", "Audi A6"]
}


def generate_plate_number():
    letters = ''.join(random.choices('ABEKMHOPCTYX', k=1)) + ''.join(random.choices(string.digits, k=3)) + ''.join(
        random.choices('ABEKMHOPCTYX', k=2)) + ''.join(random.choices(string.digits, k=2))
    return letters


def haversine(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])

    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))

    r = 6371.0

    return c * r


def get_distance(origin, dest):
    c1 = y_geocode.geocode(origin)['response']['GeoObjectCollection']['featureMember'][0]['GeoObject']['Point']['pos']
    c2 = y_geocode.geocode(dest)['response']['GeoObjectCollection']['featureMember'][0]['GeoObject']['Point']['pos']
    orig_cord = tuple(map(float, c1.split()))
    dest_cord = tuple(map(float, c2.split()))
    return haversine(orig_cord[0], orig_cord[1], dest_cord[0], dest_cord[1])


def register_user():
    questions = [
        inquirer.Text('login', message="Введите логин"),
        inquirer.Password('password', message="Введите пароль"),
    ]
    answers = inquirer.prompt(questions)

    try:
        api.register_user(session, answers['login'], answers['password'])
        print("Регистрация успешна!")
    except ValueError as e:
        print(f"Ошибка: {e}")


def login_user():
    questions = [
        inquirer.Text('login', message="Введите логин"),
        inquirer.Password('password', message="Введите пароль"),
    ]
    answers = inquirer.prompt(questions)

    try:
        user = api.authenticate_user(session, answers['login'], answers['password'])
        print("Вход выполнен успешно!")
        return user
    except ValueError as e:
        print(f"Ошибка: {e}")
        return None


def validate_card_info(card_number, card_expiry_date, card_cvv):
    if len(card_number) != 16 or not card_number.isdigit():
        return False
    if len(card_expiry_date) != 5 or card_expiry_date[2] != '/':
        return False
    if len(card_cvv) != 3 or not card_cvv.isdigit():
        return False
    return True


def enter_card_info():
    card_questions = [
        inquirer.Text('card_number', message="Введите номер карты (16 цифр)"),
        inquirer.Text('card_expiry_date', message="Введите дату окончания действия карты (MM/YY)"),
        inquirer.Text('card_cvv', message="Введите CVV код (3 цифры)")
    ]
    card_answers = inquirer.prompt(card_questions)
    return {
        'card_number': card_answers['card_number'],
        'card_expiry_date': card_answers['card_expiry_date'],
        'card_cvv': card_answers['card_cvv']
    }


def create_order(user):
    questions = [
        inquirer.Text('origin', message="Введите начальный адрес"),
        inquirer.Text('destination', message="Введите адрес назначения"),
        inquirer.List('tariff', message="Выберите тариф", choices=[tariff.value for tariff in Tariff]),
        inquirer.List('payment_method', message="Выберите способ оплаты",
                      choices=[method.value for method in PaymentMethod])
    ]
    answers = inquirer.prompt(questions)

    payment_method = PaymentMethod(answers['payment_method'])

    card_info = None
    use_saved_card = False

    if payment_method == PaymentMethod.CARD:
        saved_card_info = user.get_card_info()
        last_four_digits = user.get_last_four_digits()
        if saved_card_info['card_number']:
            use_saved_card = inquirer.prompt([inquirer.Confirm('use_saved_card',
                                                               message=f"Использовать сохраненную карту **** **** **** "
                                                                       f"{last_four_digits}?",
                                                               default=True)])['use_saved_card']
            if use_saved_card:
                card_info = saved_card_info
            else:
                card_info = enter_card_info()
        else:
            card_info = enter_card_info()

        if card_info:
            if not validate_card_info(card_info['card_number'], card_info['card_expiry_date'], card_info['card_cvv']):
                print("Неверные данные карты. Пожалуйста, попробуйте снова.")
                return
            if not use_saved_card and inquirer.prompt(
                    [inquirer.Confirm('save_card', message="Сохранить эту карту для будущих заказов?",
                                      default=False)])['save_card']:
                user.set_card_info(card_info['card_number'], card_info['card_expiry_date'], card_info['card_cvv'])
                session.commit()

    try:
        distance = get_distance(answers['origin'], answers['destination'])
        tariff = Tariff(answers['tariff'])
        price = distance * TARIFF_MULTIPLIERS[tariff] * 50
        car = random.choice(CARS[tariff])
        plate_number = generate_plate_number()

        api.user_create_order(session, user, answers['origin'], answers['destination'], price, tariff, car,
                              plate_number, payment_method)
        print(
            f"Заказ успешно создан с ценой {price:.2f} рублей за {distance:.2f} км, машина: {car},"
            f" номер: {plate_number}")

        order = session.query(Order).filter_by(initiator_id=user.id).order_by(Order.id.desc()).first()
        visualize_trip(order)
    except ValueError as e:
        print(f"Ошибка: {e}")


def visualize_trip(order):
    car_graphic = [
        "               .----' `----.",
        "              //^^^^;;^^^^^^`\\",
        "      _______//_____||_____()_\\________",
        "     /826    :      : ___              `\\",
        "    |>   ____;      ;  |/\\><|   ____   _<)",
        "   {____/    \\_________________/    \\____}",
        "        \\ '' /                 \\ '' /",
        "  jgs    '--'                   '--'"
    ]

    def display_car_graphic(progress):
        for line in car_graphic:
            print(line.replace('826', f"{progress}%"))

    try:
        print("Водитель едет к вам...")
        for i in range(5):
            display_car_graphic((i + 1) * 20)
            time.sleep(1)
            if i == 2:
                if inquirer.prompt([inquirer.Confirm('cancel', message="Хотите отменить заказ?", default=False)])[
                    'cancel'
                ]:
                    api.cancel_order(session, order.id)
                    print("Заказ успешно отменен!")
                    return

        print("Водитель едет к месту назначения...")
        for i in range(5):
            display_car_graphic((i + 1) * 20)
            time.sleep(1)

        order.status = OrderStatus.COMPLETED
        session.commit()
        print("Поездка завершена!")

        rate_driver(order)
    except ValueError as e:
        print(f"Ошибка: {e}")


def rate_driver(order):
    questions = [
        inquirer.Text('rating', message="Оцените водителя (1-5)",
                      validate=lambda _, x: x.isdigit() and 1 <= int(x) <= 5),
    ]
    answers = inquirer.prompt(questions)

    try:
        api.rate_driver(session, order.id, float(answers['rating']))
        print("Водитель успешно оценен!")
    except ValueError as e:
        print(f"Ошибка: {e}")


def view_trip_history(user):
    try:
        orders = api.get_trip_history(session, user)
        if orders:
            print("\nИстория поездок:")
            for order in orders:
                status = f"Статус: {order.status.value}"
                rating = f"Рейтинг: {order.driver_rating:.1f}" if order.driver_rating else "Рейтинг: N/A"
                tariff = f"Тариф: {order.tariff.value}"
                car = f"Машина: {order.car}"
                plate_number = f"Номер: {order.plate_number}"
                payment_method = f"Способ оплаты: {order.payment_method.value}"
                if order.payment_method == PaymentMethod.CARD:
                    last_four_digits = user.get_last_four_digits()
                    payment_method += f" (**** **** **** {last_four_digits})"
                print(
                    f"\nID заказа: {order.id}\nНачальный адрес: {order.origin}\nАдрес назначения: {order.destination}"
                    f"\nЦена: {order.price:.2f}\n{status}\n{rating}\n{tariff}\n{car}\n{plate_number}\n{payment_method}")
        else:
            print("Нет найденных поездок.")
    except Exception as e:
        print(f"Ошибка: {e}")


def main():
    parser = argparse.ArgumentParser(description="CLI для регистрации пользователей и управления заказами")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser('register', help='Зарегистрировать нового пользователя')

    subparsers.add_parser('login', help='Войти в свою учетную запись')

    subparsers.add_parser('order', help='Создать новый заказ для существующего пользователя')

    subparsers.add_parser('history', help='Просмотр истории поездок для существующего пользователя')

    args = parser.parse_args()

    if args.command == 'register':
        register_user()
    elif args.command == 'login':
        user = login_user()
        if user:
            print(f"Добро пожаловать, {user.login}!")
            while True:
                action = inquirer.prompt([inquirer.List('action', message="Что вы хотите сделать?",
                                                        choices=['Заказать такси', 'Просмотреть историю поездок',
                                                                 'Выйти'])])['action']
                if action == 'Заказать такси':
                    create_order(user)
                elif action == 'Просмотреть историю поездок':
                    view_trip_history(user)
                elif action == 'Выйти':
                    print("Выход.")
                    break
    else:
        parser.print_help()


if __name__ == '__main__':
    main()

    session.close()
