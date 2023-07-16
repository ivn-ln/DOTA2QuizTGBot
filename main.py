import logging
from aiogram import types, Bot, Dispatcher, executor
from api_token import API_TOKEN
import json
from dotabuffpy import DotaBuffTools
from jsontools import JsonTools
import random
import cv2 as cv
import numpy as np
import atexit
import os


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO,
                    filename='Logs/logs.txt')
BOT = Bot(API_TOKEN)
DISPATCHER = Dispatcher(BOT)
START_TEXT = """<b>To start the game /game</b>
<b>To view best score /best_score</b>"""
with open('JSON Files/locales.json') as file:
    LOCALES_DATA = json.load(file)
COMMANDS = LOCALES_DATA['locales']['en']['commands']
HELP_TEXT = "".join(command_description['name'] + " " + command_description['description'] + '\n'
                    for command_description in COMMANDS)
ITEMS_JSON_PATH = 'JSON Files/items.json'
HEROES_JSON_PATH = 'JSON Files/heroes.json'
MAX_ROW_AMOUNT = 4


itemdict = {}
herodict = {}
user_data_dict = {}


def single_page(func):
    async def wrapper(*args):
        message = args[0]
        if user_data_dict[str(message.chat.id)]['single_page_mode'] is False:
            await func(*args)
            return
        gen_message = await delete_previous_messages(message)
        await func(*args)
        await edit_gen_message(message, gen_message)
    return wrapper


def check_game_state(desired_state: bool, *args, **kwargs):
    def decorator(func):
        async def wrapper(message: types.Message, *a, **kw):
            global user_data_dict
            try:
                if desired_state is False:
                    if user_data_dict[str(message.chat.id)]['game_active']:
                        user_data_dict[str(message.chat.id)]['command_buffer'] = func
                        await message.answer("Cannot execute if the game is active, type /quit_game to stop the game")
                    else:
                        await func(message, *args, **kwargs)
                else:
                    if user_data_dict[str(message.chat.id)]['game_active']:
                        await func(message, *args, **kwargs)
                    else:
                        await message.answer("Cannot execute if the game is inactive, type /game to start the game")
            except Exception as e:
                logging.log(logging.CRITICAL, f"Error: {e}")
                await check_user_exists(message)
                keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
                keyboard.add(types.KeyboardButton('/game'))
                keyboard.add(types.KeyboardButton('/settings'))
                await message.answer(START_TEXT, reply_markup=keyboard, parse_mode='html')
                await message.answer(HELP_TEXT)
        return wrapper
    return decorator


@DISPATCHER.message_handler(commands=['start', 'back', 'quit'])
@check_game_state(desired_state=False)
@single_page
async def start_command(message: types.Message):
    await check_user_exists(message)
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(types.KeyboardButton('/game'))
    keyboard.add(types.KeyboardButton('/settings'))
    await message.answer(START_TEXT, reply_markup=keyboard, parse_mode='html')
    await message.answer(HELP_TEXT)


@DISPATCHER.message_handler(commands=['attempts'])
@check_game_state(desired_state=True)
async def attempts(message: types.Message):
    await message.answer(f'You have <b>{user_data_dict[str(message.chat.id)]["current_attempt_count"]} attempts</b> left!',
                         parse_mode='html')


@DISPATCHER.message_handler(commands=['best_score'])
async def best_score_command(message: types.Message):
    await message.answer(f'Your current best score is <b>{user_data_dict[str(message.chat.id)]["best_score"]}</b>!',
                         parse_mode='html')


@DISPATCHER.message_handler(commands=['settings'])
@check_game_state(desired_state=False)
@single_page
async def settings(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(types.KeyboardButton('/back'))
    keyboard.add(types.KeyboardButton('/language'))
    keyboard.add(types.KeyboardButton('/options_amount'))
    keyboard.add(types.KeyboardButton('/single_page_mode'))
    await message.answer(user_data_dict[str(message.chat.id)]["settings_text"], parse_mode='html', reply_markup=keyboard)


@DISPATCHER.message_handler(commands=['language', 'options_amount', 'single_page_mode'])
@check_game_state(desired_state=False)
async def change_settings(message: types.Message):
    global user_data_dict
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(types.KeyboardButton('/back'))
    keyboard.add(types.KeyboardButton('/language'))
    keyboard.add(types.KeyboardButton('/options_amount'))
    keyboard.add(types.KeyboardButton('/single_page_mode'))
    match message.get_command(True):
        case 'language':
            await message.answer('Type desired language: <i>en/ru</i>', parse_mode='html')
            user_data_dict[str(message.chat.id)]['listening_for_setting'] = message.get_command(True)
        case 'options_amount':
            await message.answer('Type desired options_amount: <i>number</i>', parse_mode='html')
            user_data_dict[str(message.chat.id)]['listening_for_setting'] = message.get_command(True)
        case 'single_page_mode':
            if user_data_dict[str(message.chat.id)]['single_page_mode']:
                user_data_dict[str(message.chat.id)]['single_page_mode'] = False
                await message.answer('Single page mode is now <b>off</b>!', reply_markup=keyboard, parse_mode='html')
            else:
                user_data_dict[str(message.chat.id)]['single_page_mode'] = True
                await message.answer('Single page mode is now <b>on</b>!', reply_markup=keyboard, parse_mode='html')


@DISPATCHER.message_handler(commands=["game", 'retry'])
@check_game_state(desired_state=False)
async def game(message):
    global user_data_dict
    user_data_dict[str(message.chat.id)]['game_active'] = True
    await get_build(message)


@DISPATCHER.message_handler(commands=["next"])
@check_game_state(desired_state=True)
async def next_question(message, change_score=True):
    global user_data_dict
    if user_data_dict[str(message.chat.id)]['current_attempt_count'] < 0:
        return
    await answer_correct_hero(message)
    if change_score:
        user_data_dict[str(message.chat.id)]['current_score'] +=\
            100 * max(1, user_data_dict[str(message.chat.id)]['current_attempt_count'])
    await message.answer(f'Score: <b>{user_data_dict[str(message.chat.id)]["current_score"]}</b>', parse_mode='html')
    await get_build(message)


@DISPATCHER.message_handler(commands=["skip"])
@check_game_state(desired_state=True)
async def skip_command(message: types.Message):
    global user_data_dict
    user_data_dict[str(message.chat.id)]['current_score'] -=\
        2 * max(100, 100 * (user_data_dict[str(message.chat.id)]['max_attempt_count']
                            - user_data_dict[str(message.chat.id)]['current_attempt_count'])
                + 100 * max(1, user_data_dict[str(message.chat.id)]['current_attempt_count']))
    await message.answer(f"<b>Skip penalty: {2 * max(100, 100 *  (user_data_dict[str(message.chat.id)]['max_attempt_count'] - user_data_dict[str(message.chat.id)]['current_attempt_count']))}</b>",
                         parse_mode='html')
    await next_question(message, change_score=False)


@DISPATCHER.message_handler(commands=["clear"])
@check_game_state(desired_state=False)
async def clear(message):
    for msg in range(message.message_id, 1, -1):
        try:
            await BOT.delete_message(chat_id=message.chat.id, message_id=msg)
        except:
            break
    await start_command(message)


@DISPATCHER.message_handler(commands=["quit_game"])
@check_game_state(desired_state=True)
async def quit_game(message: types.Message):
    global user_data_dict
    user_data_dict[str(message.chat.id)]['current_attempt_count'] = 0
    await check_attempts(message)
    if user_data_dict[str(message.chat.id)]['command_buffer'] != {}:
        await user_data_dict[str(message.chat.id)]['command_buffer'](message)
        user_data_dict[message.chat.id]['command_buffer'] = {}


@DISPATCHER.message_handler()
async def game_check_answer(message: types.Message):
    if not user_data_dict[str(message.chat.id)]['game_active']:
        await get_setting_value(message)
        return
    if message.text == herodict[user_data_dict[str(message.chat.id)]['current_hero']]['name']:
        await next_question(message)
    else:
        await check_attempts(message)


async def get_setting_value(message: types.Message):
    global user_data_dict
    if user_data_dict[str(message.chat.id)]['listening_for_setting'] == "":
        return
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(types.KeyboardButton('/back'))
    keyboard.add(types.KeyboardButton('/language'))
    keyboard.add(types.KeyboardButton('/options_amount'))
    keyboard.add(types.KeyboardButton('/single_page_mode'))
    match user_data_dict[str(message.chat.id)]['listening_for_setting']:
        case 'language':
            if message.text.lower() in ['en', 'ru']:
                user_data_dict[str(message.chat.id)]['language'] = message.text.lower()
                await message.answer('Option changed successfully!', reply_markup=keyboard)
            else:
                await message.answer('Invalid language', reply_markup=keyboard)
        case 'options_amount':
            try:
                options_amount = min(max(1, int(message.text)), list(herodict.keys()).__len__())
                user_data_dict[str(message.chat.id)]['answer_options_amount'] = options_amount
                user_data_dict[str(message.chat.id)]['max_attempt_count'] = options_amount // 3
                await message.answer('Option changed successfully!', reply_markup=keyboard)
            except:
                await message.answer('Invalid number', reply_markup=keyboard)
        case _:
            await message.answer('Error, invalid setting!', reply_markup=keyboard)
            logging.log(logging.CRITICAL, 'Error, invalid setting received.')
    user_data_dict[str(message.chat.id)]['listening_for_setting'] = ""


async def check_attempts(message: types.Message):
    global user_data_dict
    user_data_dict[str(message.chat.id)]['current_attempt_count'] -= 1
    if user_data_dict[str(message.chat.id)]['current_attempt_count'] > 0:
        await message.answer(f'Sorry, it`s <b>not {message.text}</b>\n'
                             f'Attempts left: <b>{user_data_dict[str(message.chat.id)]["current_attempt_count"]}</b>',
                             parse_mode='html')
    else:
        user_data_dict[str(message.chat.id)]['game_active'] = False
        await answer_correct_hero(message)
        keyboard = types.ReplyKeyboardMarkup()
        keyboard.add(types.KeyboardButton('/retry'))
        keyboard.add(types.KeyboardButton('/quit'))
        await message.answer(f"<b>Game Over!</b>\nScore: <b>{user_data_dict[str(message.chat.id)]['current_score']}</b>",
                             reply_markup=keyboard, parse_mode='html')
        if user_data_dict[str(message.chat.id)]['current_score'] > user_data_dict[str(message.chat.id)]['best_score']:
            await message.answer(f"<b>New best!</b>", parse_mode='html')
        user_data_dict[str(message.chat.id)]['best_score'] = max(user_data_dict[str(message.chat.id)]['best_score'],
                                                            user_data_dict[str(message.chat.id)]['current_score'])
        user_data_dict[str(message.chat.id)]['current_score'] = 0
        os.remove(f"Image/Build Images/{message.chat.id}.jpg")


async def delete_previous_messages(message):
    gen_message = await message.answer("Generating response...")
    for msg in range(message.message_id, 1, -1):
        try:
            await BOT.delete_message(chat_id=message.chat.id, message_id=msg)
        except:
            break
    return gen_message


@single_page
async def get_build(message: types.Message):
    global user_data_dict
    try:
        user_data_dict[str(message.chat.id)]['current_attempt_count'] = user_data_dict[str(message.chat.id)]['max_attempt_count']
        random_hero = get_random_hero_id()
        matches_list = DotaBuffTools.get_hero_recent_match_data(50, get_hero_as_http_parameter(random_hero))
        matches_ids = list(matches_list.keys())
        random_match_number = random.Random().randint(0, matches_ids.__len__()-1)
        id = list(matches_ids)[random_match_number]
        user_data_dict[str(message.chat.id)]['current_hero'] = random_hero
        user_data_dict[str(message.chat.id)]['current_match'] = id
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False, row_width=MAX_ROW_AMOUNT)
        random_heroes_options = get_random_hero_id_list(user_data_dict[str(message.chat.id)]['answer_options_amount'])
        if random_hero not in random_heroes_options:
            random_heroes_options[random.randint(0, random_heroes_options.__len__() - 1)] = random_hero
        set_answer_keyboard_layout(message, keyboard, random_heroes_options)
        keyboard.row()
        keyboard.insert(types.KeyboardButton('/skip'))
        keyboard.insert(types.KeyboardButton('/attempts'))
        keyboard.insert(types.KeyboardButton('/quit_game'))
        item_name_list = [itemdict[item]['name'] for item in matches_list[id]["itembuild"]]
        item_id_list = matches_list[id]["itembuild"]
        user_data_dict[str(message.chat.id)]['current_items'] = item_id_list
        build_image = generate_hero_items_image(item_id_list)
        cv.imwrite(f'Image/Build Images/{str(message.chat.id)}.jpg', build_image)
        item_name_list = "".join(str(item) + ' || ' for item in item_name_list).removesuffix(' || ')
        if not matches_list[id]["itembuild"]:
            await message.answer("Itembuild is empty")
            await next_question(message, change_score=False)
            return
        await message.answer(f"Game mode: <b>{matches_list[id]['game_mode']['mode']}"
                             f", {matches_list[id]['game_mode']['lobby']}</b>\n"
                             f"Game duration: <b>{matches_list[id]['duration']}</b>\n"
                             f"Items: <b>{item_name_list}</b>", parse_mode='html', reply_markup=keyboard)
        await message.answer_photo(types.InputFile(f'Image/Build Images/{str(message.chat.id)}.jpg'))
    except Exception as e:
        user_data_dict[str(message.chat.id)]['current_score'] -=\
            100 * max(1, user_data_dict[str(message.chat.id)]['current_attempt_count'])
        await message.answer(f"Sorry, an error has occurred. Error: {e}")
        await next_question(message, change_score=False)
        logging.log(logging.CRITICAL, f"Error: {e}")


async def edit_gen_message(from_message, gen_message):
    message = from_message
    await BOT.edit_message_text(chat_id=message.chat.id, message_id=gen_message.message_id,
                                text="<b>Response generated</b>", parse_mode='html')


def get_random_hero_id():
    return list(herodict.keys())[random.Random().randint(0, list(herodict.keys()).__len__() - 1)]


def get_random_hero_id_list(list_length):
    heroes_list = []
    for _ in range(list_length):
        random_hero_id = get_random_hero_id()
        while random_hero_id in heroes_list:
            random_hero_id = get_random_hero_id()
        heroes_list.append(random_hero_id)
    return heroes_list


def get_hero_as_http_parameter(hero_id):
    return hero_id.split('/')[2]


def get_hero_name(hero_id):
    return herodict[hero_id]["name"]


def set_answer_keyboard_layout(message, keyboard: types.ReplyKeyboardMarkup, random_heroes_options: list):
    random_heroes_options.sort()
    match user_data_dict[str(message.chat.id)]['answer_options_amount']:
        case 2:
            keyboard.row()
            for hero in random_heroes_options:
                hero_name = get_hero_name(hero)
                keyboard.insert(hero_name)
        case _:
            keyboard.row()
            row = 0
            for hero in random_heroes_options:
                if user_data_dict[str(message.chat.id)]['answer_options_amount'] // 2 >= MAX_ROW_AMOUNT:
                    if row % MAX_ROW_AMOUNT == 0 and row >= MAX_ROW_AMOUNT:
                        keyboard.row()
                elif row == user_data_dict[str(message.chat.id)]['answer_options_amount'] // 2:
                    keyboard.row()
                hero_name = get_hero_name(hero)
                row += 1
                keyboard.insert(hero_name)


async def answer_correct_hero(message: types.Message):
    current_match = user_data_dict[str(message.chat.id)]['current_match']
    current_hero = user_data_dict[str(message.chat.id)]['current_hero']
    current_items = user_data_dict[str(message.chat.id)]['current_items']
    keyboard = types.InlineKeyboardMarkup()
    match_url = 'www.dotabuff.com' + current_match
    keyboard.add(types.InlineKeyboardButton(text=f'Match {get_hero_as_http_parameter(current_match)}',
                                            url=match_url))
    build_image = generate_hero_items_image(current_items, current_hero)
    cv.imwrite(f'Image/Build Images/{str(message.chat.id)}.jpg', build_image)
    await message.answer_photo(types.InputFile(f'Image/Build Images/{str(message.chat.id)}.jpg'),
                               caption=f'The hero was <b>{herodict[current_hero]["name"]}</b>',
                               parse_mode='html', reply_markup=keyboard)


def update_json(items_path, heroes_path, ignore_existing):
    global herodict, itemdict
    herodict = DotaBuffTools.get_dota2_hero_data()
    JsonTools.add_dict_to_json(heroes_path, herodict, ignore_existing)
    itemdict = DotaBuffTools.get_dota2_item_data()
    JsonTools.add_dict_to_json(items_path, itemdict, ignore_existing)


async def check_user_exists(message: types.Message):
    user_id = str(message.chat.id)
    if str(user_id) in list(user_data_dict.keys()):
        await message.answer(f'Welcome to the DOTA2 item build quiz, user {user_id}!')
        return
    else:
        await message.answer('Creating new user...')
        user_vars = {}
        user_vars['game_active'] = False
        user_vars['answer_options_amount'] = 8
        user_vars['language'] = "en"
        user_vars['single_page_mode'] = True
        user_vars['current_hero'] = ""
        user_vars['current_items'] = []
        user_vars['current_match'] = ""
        user_vars['settings_text'] = f"/language <b>Current: {user_vars['language']}.</b> Change app language\n/options_amount <b>Current: {user_vars['answer_options_amount']}.</b> Change options amount given for a question(also changes attempts amount)\n/single_page_mode <b>Current: {user_vars['single_page_mode']}.</b> Change whether to delete previous messages when showing new"
        user_vars['listening_for_setting'] = ""
        user_vars['best_score'] = 0
        user_vars['current_score'] = 0
        user_vars['max_attempt_count'] = 2
        user_vars['current_attempt_count'] = 0
        user_vars['command_buffer'] = {}
        user_data_dict[user_id] = user_vars
        await message.answer(f'Welcome to the DOTA2 item build quiz, user {user_id}!')


def load_json(items_path, heroes_path):
    global herodict, itemdict
    itemdict = DotaBuffTools.get_dota2_item_data()
    herodict = DotaBuffTools.get_dota2_hero_data()
    JsonTools.add_dict_to_json(items_path, itemdict)
    JsonTools.add_dict_to_json(heroes_path, herodict)


def exit_handler():
    for user in list(user_data_dict.keys()):
        user_data_dict[user]['command_buffer'] = {}
    JsonTools.add_dict_to_json('JSON Files/users.json', user_data_dict, False)


def generate_hero_items_image(items:list, hero='unknown'):
    if hero == 'unknown':
        hero_image = cv.imread('Image/unknown.png')
    else:
        hero_image = np.uint8(np.asarray(herodict[hero]['image']))
    grid_rows = 3
    grid_lines = 2
    cell_margin_x = 10
    cell_margin_y = 9
    cell_size_x = 75
    cell_size_y = 59
    grid = cv.imread('Image/grid.png')
    label = cv.imread('Image/label.png')
    item_image_list = []
    if items.__len__() > 0:
        for item_name in items:
            item_image = np.uint8(np.asarray(itemdict[item_name]['image']))
            item_image_list.append(item_image)
    item_number = 0
    for l in range(grid_lines):
        for r in range(grid_rows):
            if item_number >= item_image_list.__len__():
                break
            item_image = item_image_list[item_number]
            item_image = cv.resize(item_image, (cell_size_x - cell_margin_x + 1, cell_size_y - cell_margin_y + 1))
            grid[cell_margin_y + cell_margin_y * l +
                 cell_size_y * l:cell_size_y + cell_size_y * l + cell_margin_y * l + 1,
                 cell_margin_x + cell_margin_x * r + cell_size_x * r:cell_size_x
                 + cell_margin_x * r + cell_size_x * r + 1] = item_image
            item_number += 1
    hero_image = cv.resize(hero_image, [257, 144])
    result = np.vstack([grid, label])
    result = np.vstack([hero_image, result])
    return result


def main():
    global herodict, itemdict, user_data_dict
    try:
        if input("To update heroes and items data print /update\n") == "/update":
            ignore_existing = bool(input("Ignore existing?(Y/N)").lower() == "y")
            update_json(ITEMS_JSON_PATH, HEROES_JSON_PATH, ignore_existing)
            logging.log(logging.INFO, "JSON data Updated and loaded")
        else:
            itemdict = JsonTools.load_dict_from_json(ITEMS_JSON_PATH)
            herodict = JsonTools.load_dict_from_json(HEROES_JSON_PATH)
            logging.log(logging.INFO, "JSON data Loaded")
        user_data_dict = JsonTools.load_dict_from_json('JSON Files/users.json')
        atexit.register(exit_handler)
        executor.start_polling(DISPATCHER, skip_updates=True)
    except Exception as e:
        logging.log(logging.CRITICAL, f"Error: {e}")


if __name__ == "__main__":
    main()
