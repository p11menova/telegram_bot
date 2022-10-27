import telebot
import requests
from PIL import Image
from io import BytesIO
from telegram_bot.const import *
from telegram_bot.small_db import *

bot = telebot.TeleBot(TOKEN, parse_mode=None)


@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "приветик! я поисковой помощник!\n"
                          "для получения инструкции по использованию введи /help")


@bot.message_handler(commands=['help'])
def welcome_help(message):
    bot.reply_to(message, 'этот бот помогает найти ближайшую организацию по запросу! \n'
                          'твое местоположение будет отмечено красной меткой, а результат поиска - темно-синей\n\n '
                          'для начала запросов ввести /reg')


@bot.message_handler(content_types=['text'])
def start(message):
    id = message.from_user.id


    if id not in USERS.keys():
        add_user(id)

    if message.text == 'неа':
        USERS[id].clean_address()

    if message.text == '/reg':
        if USERS[id].address == '':
            bot.send_message(id, "введи свой адрес!")
            bot.register_next_step_handler(message, get_user_coords)
        else:
            bot.send_message(message.from_user.id, 'что поблизости нужно найти? \n (пр. аптека, стадион, трц)')
            bot.register_next_step_handler(message, get_org_address)
    else:
        bot.send_message(id, 'напиши /reg')


def get_user_coords(message):
    id = message.from_user.id

    geocoder_params = {
        "apikey": geocoder_api_key,
        "geocode": message.text,
        "format": "json"
    }

    response = requests.get(geocoder_api_server, params=geocoder_params)
    json_response1 = response.json()

    try:
        toponym = json_response1["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]
        toponym_coodrinates = toponym["Point"]["pos"]

    except IndexError:
        bot.send_message(id, 'не валидный адрес! исправь, указав город, улицу и номер дома')
        bot.register_next_step_handler(message, get_user_coords)

    else:
        USERS[id].add_address(toponym_coodrinates)

        bot.send_message(id, 'что поблизости нужно найти? \n (пр. аптека, стадион, трц)')
        bot.register_next_step_handler(message, get_org_address)


def get_org_address(message):
    id = message.from_user.id

    search_params = {
        "apikey": api_key,
        "text": message.text,
        "lang": "ru_RU",
        "ll": ','.join(USERS[id].address.split()),
        "type": "biz"
    }

    response = requests.get(search_api_server, params=search_params)

    org_address_json = response.json()
    print(org_address_json)
    if not org_address_json['features']:
        bot.send_message(id, 'ничего не могу найти! проверь корректность задания!')
        bot.register_next_step_handler(message, get_org_address)
    else:
        static_api(message.from_user.id, org_address_json)

        keyboard = telebot.types.ReplyKeyboardMarkup(True, one_time_keyboard=True)
        keyboard.row('да!', 'неа')
        bot.send_message(message.from_user.id, 'продолжить поиск по этому адресу?', reply_markup=keyboard)


def static_api(user_id, org_address_json):
    organization = org_address_json["features"][0]
    org_name = organization["properties"]["CompanyMetaData"]["name"]
    org_address = organization["properties"]["CompanyMetaData"]["address"]

    point = organization["geometry"]["coordinates"]

    org_point = "{0},{1}".format(point[0], point[1])
    delta = "0.002"

    map_params = {
        "spn": ",".join([delta, delta]),
        "l": "map",
        "size": "650,450",
        "pt": '~'.join(["{0},pm2ntl".format(org_point), "{0},pm2rdm".format(','.join(USERS[user_id].address.split()))])
    }

    response = requests.get(map_api_server, params=map_params)

    image = Image.open(BytesIO(response.content))

    bot.send_photo(user_id, image, caption=f'ближайшая организация по запросу:\n{org_name}\nпо адресу: {org_address}')


def main():
    bot.polling(none_stop=True)


if __name__ == '__main__':
    main()
