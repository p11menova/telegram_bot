import telebot
import requests
from PIL import Image
from io import BytesIO
from telegram_bot.const import *


bot = telebot.TeleBot(TOKEN, parse_mode=None)

user_address1 = None
org_address_json = None
CHAT_ID = None

def clean():
    global user_address1, org_address_json, CHAT_ID

    user_address1 = None
    org_address_json = None
    CHAT_ID = None


@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "приветик! я поисковой помощник!")


@bot.message_handler(commands=['help'])
def welcome_help(message):
    bot.reply_to(message, 'этот бот помогает найти ближайщую организацию по запросу! \n'
                          'твое местоположение будет отмечено красной меткой, а результат поиска - темно-синей\n\n '
                          'для начала запросов ввести /reg')


@bot.message_handler(content_types=['text'])
def start(message):
    global CHAT_ID
    if message.text == 'неа':
        clean()

    if message.text == '/reg':
        if not user_address1:
            bot.send_message(message.from_user.id, "введи свой адрес!")
            bot.register_next_step_handler(message, get_user_coords)
        else:
            bot.send_message(message.from_user.id, 'что поблизости нужно найти? \n (пр. аптека, стадион, трц)')
            bot.register_next_step_handler(message, get_org_address)
    else:
        bot.send_message(message.from_user.id, 'напиши /reg')
    CHAT_ID = message.from_user.id


def get_user_coords(message):
    global user_address1

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

        user_address1 = toponym_coodrinates
    except IndexError:
        bot.send_message(message.from_user.id, 'невалидный адрес! исправь, указав город, улицу и номер дома')
        bot.register_next_step_handler(message, get_user_coords)

    else:
        bot.send_message(message.from_user.id, 'что поблизости нужно найти? \n (пр. аптека, стадион, трц)')
        bot.register_next_step_handler(message, get_org_address)


def get_org_address(message):
    global org_address_json, CHAT_ID

    search_params = {
        "apikey": api_key,
        "text": message.text,
        "lang": "ru_RU",
        "ll": ','.join(user_address1.split()),
        "type": "biz"
    }

    response = requests.get(search_api_server, params=search_params)

    org_address_json = response.json()

    static_api()

    keyboard = telebot.types.ReplyKeyboardMarkup(True, one_time_keyboard=True)
    keyboard.row('да!', 'неа')
    bot.send_message(CHAT_ID, 'продолжить поиск по этому адресу?', reply_markup=keyboard)


def static_api():
    global CHAT_ID
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
        "pt": '~'.join(["{0},pm2ntl".format(org_point), "{0},pm2rdm".format(','.join(user_address1.split()))])
    }

    response = requests.get(map_api_server, params=map_params)

    image = Image.open(BytesIO(response.content))

    bot.send_photo(CHAT_ID, image, caption=f'ближайшая организация по запросу:\n{org_name}\nпо адресу: {org_address}')


bot.polling()
