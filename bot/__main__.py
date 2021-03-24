import os
import importlib
import re
import datetime
from typing import Optional, List
import resource
import platform
import sys
import traceback
import requests
from parsel import Selector
import json
from urllib.request import urlopen

from telegram import Message, Chat, Update, Bot, User
from telegram import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from telegram.error import Unauthorized, BadRequest, TimedOut, NetworkError, ChatMigrated, TelegramError
from telegram.ext import CommandHandler, Filters, MessageHandler, CallbackQueryHandler
from telegram.ext.dispatcher import run_async, DispatcherHandlerStop, Dispatcher
from telegram.utils.helpers import escape_markdown
from bot import dispatcher, updater, TOKEN, WEBHOOK, SUDO_USERS, OWNER_ID, CERT_PATH, PORT, URL, LOGGER, OWNER_NAME, ALLOW_EXCL
from bot.modules import ALL_MODULES
from bot.modules.helper_funcs.chat_status import is_user_admin
from bot.modules.helper_funcs.misc import paginate_modules
from bot.modules.connection import connected
from bot.modules.connection import connect_button


PM_START_TEXT = """
*Salam* *{}*
*Mənim adım* *{}*!\n\n`Hər hansı bir Qrupda Filtrlər Əlavə etmək üçün dizayn edilmiş və qurulmuş sadə bir bot. Bu bota hər cür filtr əlavə edə bilərsiniz!`

_Daha çox məlumat üçün Kömək düyməsini vurun ✌️_
"""


HELP_STRINGS = """
*Salam mənim adım* *{}*!
*Mövcud əsas əmrlər aşağıdadır:*

Aşağıdakı əmrlərin hamısı / istifadə edilə bilər...

@Mr_HD_20 tərəfindən hazırlanmışdır 🔥
""".format(dispatcher.bot.first_name, "" if not ALLOW_EXCL else "\nBütün əmrlər ya / və ya ! ilə istifadə edilə bilər.\n")



VERSION = "1.0"

def vercheck() -> str:
    return str(VERSION)


SOURCE_STRING = """
*Bağışlayın amma qurucumla daha yaxşı əlaqə qurmalısınız😴*
"""


IMPORTED = {}
MIGRATEABLE = []
HELPABLE = {}
STATS = []
USER_INFO = []
DATA_IMPORT = []
DATA_EXPORT = []

CHAT_SETTINGS = {}
USER_SETTINGS = {}

GDPR = []

START_IMG = os.environ.get('START_IMG', None)
if START_IMG is None:
    img = "https://telegra.ph/file/a5455c37036b8492eb921.jpg"
else:
  img = START_IMG    
    
for module_name in ALL_MODULES:
    imported_module = importlib.import_module("bot.modules." + module_name)
    if not hasattr(imported_module, "__mod_name__"):
        imported_module.__mod_name__ = imported_module.__name__

    if not imported_module.__mod_name__.lower() in IMPORTED:
        IMPORTED[imported_module.__mod_name__.lower()] = imported_module
    else:
        raise Exception("Can't have two modules with the same name! Please change one")

    if hasattr(imported_module, "__help__") and imported_module.__help__:
        HELPABLE[imported_module.__mod_name__.lower()] = imported_module

    # Chats to migrate on chat_migrated events
    if hasattr(imported_module, "__migrate__"):
        MIGRATEABLE.append(imported_module)

    if hasattr(imported_module, "__stats__"):
        STATS.append(imported_module)

    if hasattr(imported_module, "__gdpr__"):
        GDPR.append(imported_module)

    if hasattr(imported_module, "__user_info__"):
        USER_INFO.append(imported_module)

    if hasattr(imported_module, "__import_data__"):
        DATA_IMPORT.append(imported_module)

    if hasattr(imported_module, "__export_data__"):
        DATA_EXPORT.append(imported_module)

    if hasattr(imported_module, "__chat_settings__"):
        CHAT_SETTINGS[imported_module.__mod_name__.lower()] = imported_module

    if hasattr(imported_module, "__user_settings__"):
        USER_SETTINGS[imported_module.__mod_name__.lower()] = imported_module


# do not async
def send_help(chat_id, text, keyboard=None):
    if not keyboard:
        keyboard = InlineKeyboardMarkup(paginate_modules(0, HELPABLE, "help"))
    dispatcher.bot.send_message(chat_id=chat_id,
                                text=text,
                                parse_mode=ParseMode.MARKDOWN,
                                reply_markup=keyboard)


@run_async
def test(bot: Bot, update: Update):
    # pprint(eval(str(update)))
    # update.effective_message.reply_text("Hola tester! _I_ *have* `markdown`", parse_mode=ParseMode.MARKDOWN)
    update.effective_message.reply_text("Bu şəxs bir mesajı düzəltdi")
    print(update.effective_message)


@run_async
def start(bot: Bot, update: Update, args: List[str]):
    print("Start")
    chat = update.effective_chat  # type: Optional[Chat]
    query = update.callback_query
    if update.effective_chat.type == "private":
        if len(args) >= 1:
            if args[0].lower() == "help":
                send_help(update.effective_chat.id, HELP_STRINGS)

            elif args[0].lower().startswith("stngs_"):
                match = re.match("stngs_(.*)", args[0].lower())
                chat = dispatcher.bot.getChat(match.group(1))

                if is_user_admin(chat, update.effective_user.id):
                    send_settings(match.group(1), update.effective_user.id, user=False)
                else:
                    send_settings(match.group(1), update.effective_user.id, user=True)

            elif args[0][1:].isdigit() and "rules" in IMPORTED:
                IMPORTED["rules"].send_rules(update, args[0], from_pm=True)

        else:
            send_start(bot, update)
    else:
        update.effective_message.reply_text("Hey, {} Budur...\nSizə necə kömək edə bilərəm? 🙂".format(bot.first_name),reply_markup=InlineKeyboardMarkup(
                                                [[InlineKeyboardButton(text="⚙️ Kömək ⚙️",url="t.me/{}?start=help".format(bot.username))]]))

def send_start(bot, update):
    #Try to remove old message
    try:
        query = update.callback_query
        query.message.delete()
    except:
        pass

    chat = update.effective_chat  # type: Optional[Chat]
    first_name = update.effective_user.first_name 
    text = PM_START_TEXT

    keyboard = [[InlineKeyboardButton(text="⚙️ kömək",callback_data="help_back"),InlineKeyboardButton(text="Qurucum 🧑‍💻",url="https://t.me/Mr_HD_20")]]
    keyboard += [[InlineKeyboardButton(text="♻️ bağlantı", callback_data="main_connect"),InlineKeyboardButton(text="Məni qrupa əlavə et 💠",url="t.me/{}?startgroup=true".format(bot.username))]]

    update.effective_message.reply_photo(img, PM_START_TEXT.format(escape_markdown(first_name), escape_markdown(bot.first_name), OWNER_NAME, OWNER_ID), 
                                         reply_markup=InlineKeyboardMarkup(keyboard), disable_web_page_preview=True, parse_mode=ParseMode.MARKDOWN)


def m_connect_button(bot, update):
    bot.delete_message(update.effective_chat.id, update.effective_message.message_id)
    connect_button(bot, update)


# for test purposes
def error_callback(bot, update, error):
    try:
        raise error
    except Unauthorized:
        print("no nono1")
        print(error)
        # remove update.message.chat_id from conversation list
    except BadRequest:
        print("no nono2")
        print("BadRequest caught")
        print(error)

        # handle malformed requests - read more below!
    except TimedOut:
        print("no nono3")
        # handle slow connection problems
    except NetworkError:
        print("no nono4")
        # handle other connection problems
    except ChatMigrated as err:
        print("no nono5")
        print(err)
        # the chat_id of a group has changed, use e.new_chat_id instead
    except TelegramError:
        print(error)
        # handle all other telegram related errors


@run_async
def help_button(bot: Bot, update: Update):
    query = update.callback_query
    mod_match = re.match(r"help_module\((.+?)\)", query.data)
    prev_match = re.match(r"help_prev\((.+?)\)", query.data)
    next_match = re.match(r"help_next\((.+?)\)", query.data)
    back_match = re.match(r"help_back", query.data)
    try:
        if mod_match:
            module = mod_match.group(1)
            text = "Budur *{}* modulu üçün kömək:\n".format(HELPABLE[module].__mod_name__) \
                   + HELPABLE[module].__help__
            query.message.reply_text(text=text,
                                     parse_mode=ParseMode.MARKDOWN,
                                     reply_markup=InlineKeyboardMarkup(
                                         [[InlineKeyboardButton(text="Geri", callback_data="help_back")]]))

        elif prev_match:
            curr_page = int(prev_match.group(1))
            query.message.reply_text(HELP_STRINGS,
                                     parse_mode=ParseMode.MARKDOWN,
                                     reply_markup=InlineKeyboardMarkup(
                                         paginate_modules(curr_page - 1, HELPABLE, "help")))

        elif next_match:
            next_page = int(next_match.group(1))
            query.message.reply_text(HELP_STRINGS,
                                     parse_mode=ParseMode.MARKDOWN,
                                     reply_markup=InlineKeyboardMarkup(
                                         paginate_modules(next_page + 1, HELPABLE, "help")))

        elif back_match:
            query.message.reply_text(text=HELP_STRINGS,
                                     parse_mode=ParseMode.MARKDOWN,
                                     reply_markup=InlineKeyboardMarkup(paginate_modules(0, HELPABLE, "help")))

        # ensure no spinny white circle
        bot.answer_callback_query(query.id)
        query.message.delete()
    except BadRequest as excp:
        if excp.message == "Message is not modified":
            pass
        elif excp.message == "Query_id_invalid":
            pass
        elif excp.message == "Message can't be deleted":
            pass
        else:
            LOGGER.exception("Exception in help buttons. %s", str(query.data))


@run_async
def get_help(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    args = update.effective_message.text.split(None, 1)

    # ONLY send help in PM
    if chat.type != chat.PRIVATE:

        update.effective_message.reply_text("Mümkün əmrlərin siyahısını almaq üçün PM-də mənə müraciət edin.",
                                            reply_markup=InlineKeyboardMarkup(
                                                [[InlineKeyboardButton(text="⚙️ Kömək ⚙️",url="t.me/{}?start=help".format(bot.username))],  
                                                [InlineKeyboardButton(text="🧑‍💻 Qurucum 🧑‍💻",url="https://t.me/I_Am_Only_One_1")]]))
        return

    elif len(args) >= 2 and any(args[1].lower() == x for x in HELPABLE):
        module = args[1].lower()
        text = "*{}* Modulu üçün mövcud kömək:\n".format(HELPABLE[module].__mod_name__) \
               + HELPABLE[module].__help__
        send_help(chat.id, text, InlineKeyboardMarkup([[InlineKeyboardButton(text="Geri", callback_data="help_back")]]))

    else:
        send_help(chat.id, HELP_STRINGS)


def send_settings(chat_id, user_id, user=False):
    if user:
        if USER_SETTINGS:
            settings = "\n\n".join(
                "*{}*:\n{}".format(mod.__mod_name__, mod.__user_settings__(user_id)) for mod in USER_SETTINGS.values())
            dispatcher.bot.send_message(user_id, "Bunlar cari parametrlərinizdir:" + "\n\n" + settings,
                                        parse_mode=ParseMode.MARKDOWN)

        else:
            dispatcher.bot.send_message(user_id, "Mövcud istifadəçi üçün heç bir parametr olmadığı görünür:'(",
                                        parse_mode=ParseMode.MARKDOWN)

    else:
        if CHAT_SETTINGS:
            chat_name = dispatcher.bot.getChat(chat_id).title
            dispatcher.bot.send_message(user_id,
                                        text="{} Parametrlərini hansı modul üçün yoxlamaq istərdiniz?".format(
                                            chat_name),
                                        reply_markup=InlineKeyboardMarkup(
                                            paginate_modules(0, CHAT_SETTINGS, "stngs", chat=chat_id)))
        else:
            dispatcher.bot.send_message(user_id, "Mövcud söhbət ayarları olmadığı görünür:'(\nBunu göndərin"
                                                 "cari parametrlərini tapmaq üçün qrupda admin olmalısınız!",
                                        parse_mode=ParseMode.MARKDOWN)


    


@run_async
def settings_button(bot: Bot, update: Update):
    query = update.callback_query
    user = update.effective_user
    mod_match = re.match(r"stngs_module\((.+?),(.+?)\)", query.data)
    prev_match = re.match(r"stngs_prev\((.+?),(.+?)\)", query.data)
    next_match = re.match(r"stngs_next\((.+?),(.+?)\)", query.data)
    back_match = re.match(r"stngs_back\((.+?)\)", query.data)
    try:
        if mod_match:
            chat_id = mod_match.group(1)
            module = mod_match.group(2)
            chat = bot.get_chat(chat_id)
            text = "*{}*, *{}* modulu üçün aşağıdakı parametrlərə malikdir:\n\n".format(escape_markdown(chat.title),
                                                                                     CHAT_SETTINGS[
                                                                                         module].__mod_name__) + \
                   CHAT_SETTINGS[module].__chat_settings__(chat_id, user.id)
            query.message.reply_text(text=text,
                                     parse_mode=ParseMode.MARKDOWN,
                                     reply_markup=InlineKeyboardMarkup(
                                         [[InlineKeyboardButton(text="Geri",
                                                                callback_data="stngs_back({})".format(chat_id))]]))

        elif prev_match:
            chat_id = prev_match.group(1)
            curr_page = int(prev_match.group(2))
            chat = bot.get_chat(chat_id)
            query.message.reply_text("Salam! {} Üçün bir neçə parametr var - davam edin və nəyisə seçin"
                                     "maraqlanırsan".format(chat.title),
                                     reply_markup=InlineKeyboardMarkup(
                                         paginate_modules(curr_page - 1, CHAT_SETTINGS, "stngs",
                                                          chat=chat_id)))

        elif next_match:
            chat_id = next_match.group(1)
            next_page = int(next_match.group(2))
            chat = bot.get_chat(chat_id)
            query.message.reply_text("Salam! {} Üçün bir neçə parametr var - davam edin və nəyisə seçin"
                                     "maraqlanırsan".format(chat.title),
                                     reply_markup=InlineKeyboardMarkup(
                                         paginate_modules(next_page + 1, CHAT_SETTINGS, "stngs",
                                                          chat=chat_id)))

        elif back_match:
            chat_id = back_match.group(1)
            chat = bot.get_chat(chat_id)
            query.message.reply_text(text="Salam! {} Üçün bir neçə parametr var - davam edin və nəyisə seçin"
                                          "maraqlanırsan".format(escape_markdown(chat.title)),
                                     parse_mode=ParseMode.MARKDOWN,
                                     reply_markup=InlineKeyboardMarkup(paginate_modules(0, CHAT_SETTINGS, "stngs",
                                                                                        chat=chat_id)))

        # ensure no spinny white circle
        bot.answer_callback_query(query.id)
        query.message.delete()
    except BadRequest as excp:
        if excp.message == "Message is not modified":
            pass
        elif excp.message == "Query_id_invalid":
            pass
        elif excp.message == "Message can't be deleted":
            pass
        else:
            LOGGER.exception("Exception in settings buttons. %s", str(query.data))


@run_async
def get_settings(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]
    args = msg.text.split(None, 1)

    # ONLY send settings in PM
    if chat.type != chat.PRIVATE:
        if is_user_admin(chat, user.id):
            text = "Click here to get this chat's settings, as well as yours."
            msg.reply_text(text,
                           reply_markup=InlineKeyboardMarkup(
                               [[InlineKeyboardButton(text="⚙️ Ayarlar ⚙️",
                                                      url="t.me/{}?start=stngs_{}".format(
                                                          bot.username, chat.id))]]))
        else:
            text = "Ayarlarınızı yoxlamaq üçün buraya vurun."

    else:
        send_settings(chat.id, user.id, True)




def migrate_chats(bot: Bot, update: Update):
    msg = update.effective_message  # type: Optional[Message]
    if msg.migrate_to_chat_id:
        old_chat = update.effective_chat.id
        new_chat = msg.migrate_to_chat_id
    elif msg.migrate_from_chat_id:
        old_chat = msg.migrate_from_chat_id
        new_chat = update.effective_chat.id
    else:
        return

    LOGGER.info("%s -dən %s -ə köçürülür", str(old_chat), str(new_chat))
    for mod in MIGRATEABLE:
        mod.__migrate__(old_chat, new_chat)

    LOGGER.info("Uğurla köçürüldù!")
    raise DispatcherHandlerStop


@run_async
def source(bot: Bot, update: Update):
    user = update.effective_message.from_user
    chat = update.effective_chat  # type: Optional[Chat]

    if chat.type == "private":
        update.effective_message.reply_text(SOURCE_STRING, parse_mode=ParseMode.MARKDOWN)

    else:
        try:
            bot.send_message(user.id, SOURCE_STRING, parse_mode=ParseMode.MARKDOWN)

            update.effective_message.reply_text("PM-də tapa bilərsiniz.")
        except Unauthorized:
            update.effective_message.reply_text("Əvvəlcə PM-də mənə müraciət edin.")

@run_async
def imdb_searchdata(bot: Bot, update: Update):
    query_raw = update.callback_query
    query = query_raw.data.split('$')
    print(query)
    if query[1] != query_raw.from_user.username:
        return
    title = ''
    rating = ''
    date = ''
    synopsis = ''
    url_sel = 'https://www.imdb.com/title/%s/' % (query[0])
    text_sel = requests.get(url_sel).text
    selector_global = Selector(text = text_sel)
    title = selector_global.xpath('//div[@class="title_wrapper"]/h1/text()').get().strip()
    try:
        rating = selector_global.xpath('//div[@class="ratingValue"]/strong/span/text()').get().strip()
    except:
        rating = '-'
    try:
        date = '(' + selector_global.xpath('//div[@class="title_wrapper"]/h1/span/a/text()').getall()[-1].strip() + ')'
    except:
        date = selector_global.xpath('//div[@class="subtext"]/a/text()').getall()[-1].strip()
    try:
        synopsis_list = selector_global.xpath('//div[@class="summary_text"]/text()').getall()
        synopsis = re.sub(' +',' ', re.sub(r'\([^)]*\)', '', ''.join(sentence.strip() for sentence in synopsis_list)))
    except:
        synopsis = '_No synopsis available._'
    movie_data = '*%s*, _%s_\n★ *%s*\n\n%s' % (title, date, rating, synopsis)
    query_raw.edit_message_text(
        movie_data, 
        parse_mode=ParseMode.MARKDOWN
    )

@run_async
def imdb(bot: Bot, update: Update, args):
    message = update.effective_message
    query = ''.join([arg + '_' for arg in args]).lower()
    if not query:
        bot.send_message(
            message.chat.id,
            'Bir film/şou adı göstərməlisiniz!'
        )
        return
    url_suggs = 'https://v2.sg.media-imdb.com/suggests/%s/%s.json' % (query[0], query)
    json_url = urlopen(url_suggs)
    suggs_raw = ''
    for line in json_url:
        suggs_raw = line
    skip_chars = 6 + len(query)
    suggs_dict = json.loads(suggs_raw[skip_chars:][:-1])
    if suggs_dict:
        button_list = [[
                InlineKeyboardButton(
                    text = str(sugg['l'] + ' (' + str(sugg['y']) + ')'), 
                    callback_data = str(sugg['id']) + '$' + str(message.from_user.username)
                )] for sugg in suggs_dict['d'] if 'y' in sugg
        ]
        reply_markup = InlineKeyboardMarkup(button_list)
        bot.send_message(
            message.chat.id,
            'Hansı? ',
            reply_markup = reply_markup
        )
    else:
        pass             
            
            
# Avoid memory dead
def memory_limit(percentage: float):
    if platform.system() != "Linux":
        print('Yalnız Linuxda işləyir!')
        return
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    resource.setrlimit(resource.RLIMIT_AS, (int(get_memory() * 1024 * percentage), hard))

def get_memory():
    with open('/proc/meminfo', 'r') as mem:
        free_memory = 0
        for i in mem:
            sline = i.split()
            if str(sline[0]) in ('MemFree', 'Buffon:', 'Saxlandı:'):
                free_memory += int(sline[1])
    return free_memory

def memory(percentage=0.5):
    def decorator(function):
        def wrapper(*args, **kwargs):
            memory_limit(percentage)
            try:
                function(*args, **kwargs)
            except MemoryError:
                mem = get_memory() / 1024 /1024
                print('Remain: %.2f GB' % mem)
                sys.stderr.write('\n\nXATA: Yaddaş İstisnası\n')
                sys.exit(1)
        return wrapper
    return decorator


@memory(percentage=0.8)
def main():
    test_handler = CommandHandler("test", test)
    start_handler = CommandHandler("start", start, pass_args=True)
    
    IMDB_HANDLER = CommandHandler('imdb', imdb, pass_args=True)
    IMDB_SEARCHDATAHANDLER = CallbackQueryHandler(imdb_searchdata)
   
    start_callback_handler = CallbackQueryHandler(send_start, pattern=r"bot_start")
    dispatcher.add_handler(start_callback_handler)


    help_handler = CommandHandler("help", get_help)
    help_callback_handler = CallbackQueryHandler(help_button, pattern=r"help_")

    settings_handler = CommandHandler("settings", get_settings)
    settings_callback_handler = CallbackQueryHandler(settings_button, pattern=r"stngs_")
   
    source_handler = CommandHandler("source", source)
    
    migrate_handler = MessageHandler(Filters.status_update.migrate, migrate_chats)

    M_CONNECT_BTN_HANDLER = CallbackQueryHandler(m_connect_button, pattern=r"main_connect")

    # dispatcher.add_handler(test_handler)
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(help_handler)
    dispatcher.add_handler(settings_handler)
    dispatcher.add_handler(help_callback_handler)
    dispatcher.add_handler(settings_callback_handler)
    dispatcher.add_handler(migrate_handler)
    dispatcher.add_handler(source_handler)
    dispatcher.add_handler(M_CONNECT_BTN_HANDLER)
    dispatcher.add_handler(IMDB_HANDLER)
    dispatcher.add_handler(IMDB_SEARCHDATAHANDLER)
    

    # dispatcher.add_error_handler(error_callback)

    if WEBHOOK:
        LOGGER.info("Vebdən istifadə.")
        updater.start_webhook(listen="127.0.0.1",
                              port=PORT,
                              url_path=TOKEN)

        if CERT_PATH:
            updater.bot.set_webhook(url=URL + TOKEN,
                                    certificate=open(CERT_PATH, 'rb'))
        else:
            updater.bot.set_webhook(url=URL + TOKEN)

    else:
        LOGGER.info("Bot işləyir...")
        updater.start_polling(timeout=15, read_latency=4)

    updater.idle()

    
if __name__ == '__main__':
    LOGGER.info("Modullar uğurla yükləndi: " + str(ALL_MODULES))
    main()
