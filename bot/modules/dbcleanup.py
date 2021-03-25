from time import sleep

from telegram import Bot, Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import BadRequest, Unauthorized
from telegram.ext import CommandHandler, CallbackQueryHandler, run_async

from bot import dispatcher, OWNER_ID, DEV_USERS
from bot.modules.helper_funcs.chat_status import dev_plus

def get_invalid_chats(bot: Bot, update: Update, remove: bool = False):

    chat_id = update.effective_chat.id
    chats = user_sql.get_all_chats()
    kicked_chats, progress = 0, 0
    chat_list = []
    progress_message = None

    for chat in chats:

        if ((100*chats.index(chat))/len(chats)) > progress:
            progress_bar = f"{progress}% etibarsız söhbətlərin əldə edilməsi tamamlandı."
            if progress_message:
                try:
                    bot.editMessageText(progress_bar, chat_id, progress_message.message_id)
                except:
                    pass
            else:
                progress_message = bot.sendMessage(chat_id, progress_bar)
            progress += 5
        
        id = chat.chat_id
        sleep(0.1)
        try:
            bot.get_chat(id, timeout=60)
        except (BadRequest, Unauthorized):
            kicked_chats += 1
            chat_list.append(id)
        except:
            pass
    
    try:
        progress_message.delete()
    except:
        pass

    if not remove:
        return kicked_chats
    else:
        for muted_chat in chat_list:
            sleep(0.1)
            user_sql.rem_chat(muted_chat)
        return kicked_chats


def get_invalid_gban(bot: Bot, update: Update, remove: bool = False):

    banned = gban_sql.get_gban_list()
    ungbanned_users = 0
    ungban_list = []

    for user in banned:
        user_id = user["user_id"]
        sleep(0.1)
        try:
            bot.get_chat(user_id)
        except BadRequest:
            ungbanned_users += 1
            ungban_list.append(user_id)
        except:
            pass

    if not remove:
        return ungbanned_users
    else:
        for user_id in ungban_list:
            sleep(0.1)
            gban_sql.ungban_user(user_id)
        return ungbanned_users


@run_async
@dev_plus
def dbcleanup(bot: Bot, update: Update):

    msg = update.effective_message

    msg.reply_text("Yalnış söhbət sayının alınması ...")
    invalid_chat_count = get_invalid_chats(bot, update)

    msg.reply_text("Etibarsız sayılmış sayma alınır ...")
    invalid_gban_count = get_invalid_gban(bot, update)

    reply = "Total invalid chats - {}\n".format(invalid_chat_count)
    reply += "Total invalid gbanned users - {}".format(invalid_gban_count)

    buttons = [
        [InlineKeyboardButton("Təmizləmə DB", callback_data=f"db_cleanup")]
    ]

    update.effective_message.reply_text(reply, reply_markup=InlineKeyboardMarkup(buttons))


def get_muted_chats(bot: Bot, update: Update, leave: bool = False):

    chat_id = update.effective_chat.id
    chats = user_sql.get_all_chats()
    muted_chats, progress = 0, 0
    chat_list = []
    progress_message = None

    for chat in chats:

        if ((100*chats.index(chat))/len(chats)) > progress:
            progress_bar = f"{progress}% səssiz söhbətin əldə edilməsi tamamlandı."
            if progress_message:
                try:
                    bot.editMessageText(progress_bar, chat_id, progress_message.message_id)
                except:
                    pass
            else:
                progress_message = bot.sendMessage(chat_id, progress_bar)
            progress += 5

        id = chat.chat_id
        sleep(0.1)

        try:
            bot.send_chat_action(id, "YAZIR", timeout=60)
        except (BadRequest, Unauthorized):
            muted_chats += +1
            chat_list.append(id)
        except:
            pass

    try:
        progress_message.delete()
    except:
        pass

    if not leave:
        return muted_chats
    else:
        for muted_chat in chat_list:
            sleep(0.1)
            try:
                bot.leaveChat(muted_chat, timeout=60)
            except:
                pass
            user_sql.rem_chat(muted_chat)
        return muted_chats


@run_async
@dev_plus
def leave_muted_chats(bot: Bot, update: Update):

    message = update.effective_message
    progress_message = message.reply_text("Söhbət sayının əldə edilməsi ...")
    muted_chats = get_muted_chats(bot, update)

    buttons = [
        [InlineKeyboardButton("Leave chats", callback_data=f"db_leave_chat")]
    ]

    update.effective_message.reply_text(f"{muted_chats} söhbətlərində səssiz qaldım.", reply_markup=InlineKeyboardMarkup(buttons))
    progress_message.delete()


@run_async
def callback_button(bot: Bot, update: Update):

    query = update.callback_query
    message = query.message
    chat_id = update.effective_chat.id
    query_type = query.data

    admin_list = [OWNER_ID] + DEV_USERS
    
    bot.answer_callback_query(query.id)
    
    if query_type == "db_leave_chat":
        if query.from_user.id in admin_list:
            bot.editMessageText("Söhbəti tərk etmək ...", chat_id, message.message_id)
            chat_count = get_muted_chats(bot, update, True)
            bot.sendMessage(chat_id, f"Geridə {chat_count} söhbətləri.")
        else:
            query.answer("Bunu etməyinizə icazə verilmir!")
    elif query_type == "db_cleanup":
        if query.from_user.id in admin_list:
            bot.editMessageText("DB-nin təmizlənməsi ...", chat_id, message.message_id)
            invalid_chat_count = get_invalid_chats(bot, update, True)
            invalid_gban_count = get_invalid_gban(bot, update, True)
            reply = "Cleaned up {} chats and {} gbanned users from db.".format(invalid_chat_count, invalid_gban_count)
            bot.sendMessage(chat_id, reply)
        else:
            query.answer("Bunu etməyinizə icazə verilmir!")



DB_CLEANUP_HANDLER = CommandHandler("dbcleanup", dbcleanup)
LEAVE_MUTED_CHATS_HANDLER = CommandHandler("leavemutedchats", leave_muted_chats)
BUTTON_HANDLER = CallbackQueryHandler(callback_button, pattern='db_.*')

dispatcher.add_handler(DB_CLEANUP_HANDLER)
dispatcher.add_handler(LEAVE_MUTED_CHATS_HANDLER)
dispatcher.add_handler(BUTTON_HANDLER)

__mod_name__ = "Verilənlər bazası"
__handlers__ = [DB_CLEANUP_HANDLER, LEAVE_MUTED_CHATS_HANDLER, BUTTON_HANDLER]
