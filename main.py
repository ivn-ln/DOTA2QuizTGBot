from aiogram import types, Bot, Dispatcher, executor
from api_token import API_TOKEN
from requests_html import HTMLSession
from bs4 import BeautifulSoup
import logging
import json
import dotabuffpy


BOT = Bot(API_TOKEN)
DISPATCHER = Dispatcher(BOT)
START_TEXT = """Hello, welcome to my bot"""
with open('locales.json') as file:
    locales_data = json.load(file)
COMMANDS = locales_data['locales']["en"]['commands']
HELP_TEXT = ""
for command_description in COMMANDS:
    HELP_TEXT += command_description['name'] + " => " + command_description['description'] + '\n'
DOTABUFF = "https://www.dotabuff.com/matches"
DBTOOLS = dotabuffpy.DotaBuffTools()
ITEMLIST = DBTOOLS.get_dota2_item_names()


class GameModes:
    RANKED, NONRANKED, TURBO = range(3)


@DISPATCHER.message_handler(commands=['start'])
async def start_command(message):
    await message.answer(START_TEXT)


@DISPATCHER.message_handler(commands=['help'])
async def help_command(message: types.Message):
    await message.reply(HELP_TEXT)


@DISPATCHER.message_handler(commands=["getbuild"])
async def get_build(message: types.Message):
    session = HTMLSession()
    r = session.get(url=DOTABUFF, params={"hero": "abaddon"})
    soup = BeautifulSoup(markup=r.text, parser="html.parser", features="lxml")
    items_list = soup.tbody.find_all("tr")[1].find(class_="r-stats-grid").find_all(class_="image-container")
    for item in items_list:
        await message.answer(item.a["href"])


def main():
    try:
        executor.start_polling(DISPATCHER, skip_updates=True)
    except Exception as e:
        logging.log(logging.CRITICAL, f"Error: {e}")


if __name__ == "__main__":
    print(ITEMLIST)
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.WARNING)
    main()
