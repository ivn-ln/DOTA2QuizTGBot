from aiogram import types, Bot, Dispatcher, executor
from api_token import API_TOKEN
import logging
import json


class Locales:
    EN = "en"
    ES = "es"


class States:
    INACTIVE, ACTIVE = range(2)


class Settings:
    LOCALE = "Locale"


BOT = Bot(API_TOKEN)
DISPATCHER = Dispatcher(BOT)
START_TEXT = """Hello, welcome to my bot"""
LOCALE = Locales.EN
with open('locales.json') as file:
    locales_data = json.load(file)
COMMANDS = locales_data['locales'][LOCALE]['commands']
HELP_TEXT = ""
for command_description in COMMANDS:
    HELP_TEXT += command_description['name'] + " => " + command_description['description'] + '\n'
SETTINGS_TEXT = f"""
### SETTINGS ###
### TO CHANGE A SETTING, TYPE: /settings setting_name=value###
Locale: {LOCALE}
### Possible values: en, es ###
"""
SETTINGS_AMOUNT = getattr(Settings, "LOCALE")

state = States.INACTIVE


def function_error(from_func):
    logging.log(logging.WARNING, f"Error, denied access to function {from_func.__name__}")


def command_check_app_active(command):
    global state
    print(state)
    async def wrapper(*args, **kwargs):
        global state
        if state == States.ACTIVE:
            await command(*args, **kwargs)

    return wrapper


@DISPATCHER.message_handler(commands=['start'])
async def start_command(message):
    await message.answer(START_TEXT)
    global state
    state = States.ACTIVE


@DISPATCHER.message_handler(commands=['help'])
@command_check_app_active
async def help_command(message: types.Message):
    await message.reply(HELP_TEXT)


@DISPATCHER.message_handler(commands=['settings'])
async def settings_command(message: types.Message):
    await message.delete()
    await message.answer(SETTINGS_TEXT)


def main():
    try:
        executor.start_polling(DISPATCHER)
    except Exception as e:
        logging.log(logging.CRITICAL, f"Error: {e}")


if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.WARNING)
    main()
