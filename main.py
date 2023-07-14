import random
from aiogram import types, Bot, Dispatcher, executor
from api_token import API_TOKEN
import logging
import json
from dotabuffpy import DotaBuffTools


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
BOT = Bot(API_TOKEN)
DISPATCHER = Dispatcher(BOT)
START_TEXT = """Welcome to the DOTA2 Quiz TG Bot!
<b>To start the game type /game</b>"""
with open('JSON Files/locales.json') as file:
    LOCALES_DATA = json.load(file)
COMMANDS = LOCALES_DATA['locales']['en']['commands']
HELP_TEXT = "".join(command_description['name'] + " " + command_description['description'] + '\n'
                    for command_description in COMMANDS)
ITEMS_JSON_PATH = 'JSON Files/items.json'
HEROES_JSON_PATH = 'JSON Files/heroes.json'
MAX_ROW_AMOUNT = 8
MAX_ATTEMPT_COUNT = 2


itemdict = {}
herodict = {}
game_active: bool = False
answer_options_amount = 8
language = "en"
single_page_mode = True
current_hero = ""
current_match = ""
settings_text = f"""
/language <b>Current: {language}.</b> Change app language
/options_amount <b>Current: {answer_options_amount}.</b> Change options amount given for a question
/single_page_mode <b>Current: {single_page_mode}.</b> Change whether to delete previous messages when showing new page
"""
listening_for_setting = ""
best_score = 0
current_score = 0
current_attempt_count = 0


def single_page(func):
    async def wrapper(*args):
        if single_page_mode is False:
            await func(*args)
            return
        message = args[0]
        gen_message = await delete_previous_messages(message)
        await func(*args)
        await edit_gen_message(message, gen_message)
    return wrapper


def check_game_state(desired_state: bool):
    def decorator(func):
        async def wrapper(*args):
            global game_active
            message = args[0]
            if desired_state is False:
                if game_active:
                    await message.answer("Cannot execute if the game is active, type /quit_game to stop the game")
                else:
                    await func(*args)
            else:
                if game_active:
                    await func(*args)
                else:
                    await message.answer("Cannot execute if the game is inactive, type /game to start the game")
        return wrapper
    return decorator


@DISPATCHER.message_handler(commands=['start', 'back', 'quit'])
@check_game_state(desired_state=False)
@single_page
async def start_command(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(types.KeyboardButton('/game'))
    keyboard.add(types.KeyboardButton('/settings'))
    await message.answer(START_TEXT, reply_markup=keyboard, parse_mode='html')
    await message.answer(HELP_TEXT)

@check_game_state(desired_state=True)
@DISPATCHER.message_handler(commands=['attempts'])
async def best_score(message: types.Message):
    await message.answer(f'You have <b>{current_attempt_count} attempts</b> left!', parse_mode='html')


@DISPATCHER.message_handler(commands=['best_score'])
async def best_score(message: types.Message):
    await message.answer(f'Your current best score is <b>{best_score}</b>!', parse_mode='html')


@DISPATCHER.message_handler(commands=['settings'])
@check_game_state(desired_state=False)
@single_page
async def settings(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(types.KeyboardButton('/back'))
    keyboard.add(types.KeyboardButton('/language'))
    keyboard.add(types.KeyboardButton('/options_amount'))
    keyboard.add(types.KeyboardButton('/single_page_mode'))
    await message.answer(settings_text, parse_mode='html', reply_markup=keyboard)


@DISPATCHER.message_handler(commands=['language', 'options_amount', 'single_page_mode'])
@check_game_state(desired_state=False)
async def change_settings(message: types.Message):
    global single_page_mode, listening_for_setting
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(types.KeyboardButton('/back'))
    keyboard.add(types.KeyboardButton('/language'))
    keyboard.add(types.KeyboardButton('/options_amount'))
    keyboard.add(types.KeyboardButton('/single_page_mode'))
    match message.get_command(True):
        case 'language':
            await message.answer('Type desired language: <i>en/ru</i>', parse_mode='html')
            listening_for_setting = message.get_command(True)
        case 'options_amount':
            await message.answer('Type desired options_amount: <i>number</i>', parse_mode='html')
            listening_for_setting = message.get_command(True)
        case 'single_page_mode':
            if single_page_mode:
                single_page_mode = False
                await message.answer('Single page mode is now <b>off</b>!', reply_markup=keyboard, parse_mode='html')
            else:
                single_page_mode = True
                await message.answer('Single page mode is now <b>on</b>!', reply_markup=keyboard, parse_mode='html')


@DISPATCHER.message_handler(commands=["game", 'retry'])
@check_game_state(desired_state=False)
async def game(message):
    global game_active
    game_active = True
    await get_build(message)


@DISPATCHER.message_handler(commands=["next"])
@check_game_state(desired_state=True)
async def next_question(message, change_score=True):
    global current_score, current_attempt_count
    if current_attempt_count < 0:
        return
    await answer_correct_hero(message)
    if change_score:
        current_score += 100 * max(1, current_attempt_count)
        await message.answer(f'Score: <b>{current_score}</b>', parse_mode='html')
    await get_build(message)


@DISPATCHER.message_handler(commands=["skip"])
@check_game_state(desired_state=True)
async def skip(message: types.Message):
    global current_score
    current_score -= 300
    await message.answer(f'<b>Skip penalty -300</b>\nScore: <b>{current_score}</b>', parse_mode='html')
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
    global current_attempt_count
    current_attempt_count = 0
    await check_attempts(message)


@DISPATCHER.message_handler()
async def game_check_answer(message: types.Message):
    if not game_active:
        await get_setting_value(message)
        return
    if message.text == herodict[current_hero]["name"]:
        await next_question(message)
    else:
        await check_attempts(message)


async def get_setting_value(message: types.Message):
    global language, answer_options_amount, listening_for_setting
    if listening_for_setting == "":
        return
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(types.KeyboardButton('/back'))
    keyboard.add(types.KeyboardButton('/language'))
    keyboard.add(types.KeyboardButton('/options_amount'))
    keyboard.add(types.KeyboardButton('/single_page_mode'))
    match listening_for_setting:
        case 'language':
            if message.text.lower() in ['en', 'ru']:
                language = message.text.lower()
                await message.answer('Option changed successfully!', reply_markup=keyboard)
            else:
                await message.answer('Invalid language', reply_markup=keyboard)
        case 'options_amount':
            try:
                options_amount = min(max(1, int(message.text)), list(herodict.keys()).__len__())
                answer_options_amount = options_amount
                global MAX_ATTEMPT_COUNT
                MAX_ATTEMPT_COUNT = answer_options_amount//4
                await message.answer('Option changed successfully!', reply_markup=keyboard)
            except:
                await message.answer('Invalid number', reply_markup=keyboard)
        case _:
            await message.answer('Error, invalid setting!', reply_markup=keyboard)
            logging.log(logging.CRITICAL, 'Error, invalid setting received.')
    listening_for_setting = ""


def update_json():
    global herodict, itemdict
    itemdict = DotaBuffTools.get_dota2_item_data()
    herodict = DotaBuffTools.get_dota2_hero_data()


async def check_attempts(message: types.Message):
    global current_attempt_count, best_score, current_score, game_active
    current_attempt_count -= 1
    if current_attempt_count > 0:
        await message.answer(f'Sorry, it`s <b>not {message.text}</b>\n'
                             f'Attempts left: <b>{current_attempt_count}</b>',
                             parse_mode='html')
    else:
        game_active = False
        await answer_correct_hero(message)
        keyboard = types.ReplyKeyboardMarkup()
        keyboard.add(types.KeyboardButton('/retry'))
        keyboard.add(types.KeyboardButton('/quit'))
        await message.answer(f"<b>Game Over!</b>\nScore: <b>{current_score}</b>",
                             reply_markup=keyboard, parse_mode='html')
        if current_score > best_score:
            await message.answer(f"<b>New best!</b>", parse_mode='html')
        best_score = max(best_score, current_score)
        current_score = 0


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
    global current_hero, current_match, current_attempt_count
    try:
        current_attempt_count = MAX_ATTEMPT_COUNT
        random_hero = get_random_hero_id()
        matches_list = DotaBuffTools.get_hero_recent_match_data(50, get_hero_as_http_parameter(random_hero),
                                                                game_mode='turbo')
        matches_ids = list(matches_list.keys())
        random_match_number = random.Random().randint(0, matches_ids.__len__()-1)
        id = list(matches_ids)[random_match_number]
        current_hero = random_hero
        current_match = id
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False, row_width=MAX_ROW_AMOUNT)
        random_heroes_options = get_random_hero_id_list(answer_options_amount)
        if random_hero not in random_heroes_options:
            random_heroes_options[random.randint(0, random_heroes_options.__len__() - 1)] = random_hero
        set_answer_keyboard_layout(keyboard, random_heroes_options)
        keyboard.row()
        keyboard.insert(types.KeyboardButton('/skip'))
        keyboard.insert(types.KeyboardButton('/attempts'))
        keyboard.insert(types.KeyboardButton('/quit_game'))
        if not matches_list[id]["itembuild"]:
            await message.answer("Itembuild is empty")
        item_name_list = [itemdict[item]['name'] for item in matches_list[id]["itembuild"]]
        item_image_list = [types.InputMediaPhoto(itemdict[item]['image'], caption=itemdict[item]["name"])
                           for item in matches_list[id]["itembuild"]]
        item_name_list = "".join(str(item) + ' || ' for item in item_name_list).removesuffix(' || ')
        await message.answer(f"Game mode: <b>{matches_list[id]['game_mode']['mode']}</b>\n"
                             f"Game duration: <b>{matches_list[id]['duration']}</b>\n"
                             f"Items: <b>{item_name_list}</b>", parse_mode='html', reply_markup=keyboard)
        await message.answer_media_group(item_image_list)
    except Exception as e:
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


def set_answer_keyboard_layout(keyboard: types.ReplyKeyboardMarkup, random_heroes_options: list):
    match answer_options_amount:
        case 2:
            keyboard.row()
            for hero in random_heroes_options:
                hero_name = get_hero_name(hero)
                keyboard.insert(hero_name)
        case _:
            keyboard.row()
            row = 0
            for hero in random_heroes_options:
                if answer_options_amount // 2 >= MAX_ROW_AMOUNT:
                    if row % MAX_ROW_AMOUNT == 0 and row >= MAX_ROW_AMOUNT:
                        keyboard.row()
                elif row == answer_options_amount // 2:
                    keyboard.row()
                hero_name = get_hero_name(hero)
                row += 1
                keyboard.insert(hero_name)


async def answer_correct_hero(message: types.Message):
    keyboard = types.InlineKeyboardMarkup()
    match_url = 'www.dotabuff.com' + current_match
    keyboard.add(types.InlineKeyboardButton(text=f'Match {get_hero_as_http_parameter(current_match)}',
                                            url=match_url))
    await message.answer_photo(herodict[current_hero]['image'],
                               caption=f'The hero was <b>{herodict[current_hero]["name"]}</b>',
                               parse_mode='html', reply_markup=keyboard)


def main():
    try:
        update_json()
        executor.start_polling(DISPATCHER, skip_updates=True)
    except Exception as e:
        logging.log(logging.CRITICAL, f"Error: {e}")


if __name__ == "__main__":
    main()
