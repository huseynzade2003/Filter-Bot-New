import time
import re

from typing import List

from telegram import Bot, Update, ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import BadRequest, Unauthorized
from telegram.ext import CommandHandler, CallbackQueryHandler, Filters, run_async
from telegram.utils.helpers import mention_html

import bot.modules.sql.connection_sql as sql
from bot import dispatcher, SUDO_USERS, DEV_USERS, spamfilters
from bot.modules.helper_funcs import chat_status
from bot.modules.helper_funcs.extraction import extract_user, extract_user_and_text
from bot.modules.helper_funcs.string_handling import extract_time

from bot.modules.helper_funcs.alternate import send_message

user_admin = chat_status.user_admin


@user_admin
@run_async
def allow_connections(bot: Bot, update: Update, args: List[str]):

    chat = update.effective_chat

    if chat.type != chat.PRIVATE:
        if len(args) >= 1:
            var = args[0]
            if var == "no":
                sql.set_allow_connect_to_chat(chat.id, False)
                send_message(update.effective_message, "Bağlantı Uğurla *KƏSİLDİ*")
            elif var == "yes":
                sql.set_allow_connect_to_chat(chat.id, True)
                send_message(update.effective_message, "Bağlantı Uğurlu olfu")
            else:
                send_message(update.effective_message, "Zəhmət olmasa `yes` və ya `no` yazın!", parse_mode=ParseMode.MARKDOWN)
        else:
            get_settings = sql.allow_connect_to_chat(chat.id)
            if get_settings:
                send_message(update.effective_message, "Bu qrupa qoşulma üzvlər üçün *İcazə verilir*!", parse_mode=ParseMode.MARKDOWN)
            else:
                send_message(update.effective_message, "Bu qrupa qoşulma üzvlər üçün *İcazə verilmir*!", parse_mode=ParseMode.MARKDOWN)
    else:
        send_message(update.effective_message, "Bu əmr yalnız qrup üçündür. PM-də deyil!")


@run_async
def connection_chat(bot: Bot, update: Update):

    chat = update.effective_chat
    user = update.effective_user

    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return
    
    conn = connected(bot, update, chat, user.id, need_admin=True)

    if conn:
        chat = dispatcher.bot.getChat(conn)
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        if update.effective_message.chat.type != "private":
            return
        chat = update.effective_chat
        chat_name = update.effective_message.chat.title

    if conn:
        message = "Hazırda {} ilə əlaqə qurmusunuz.\n".format(chat_name)
    else:
        message = "Hal-hazırda heç bir qrupa bağlı deyilsiniz.\n"
    send_message(update.effective_message, message, parse_mode="markdown")


@run_async
def connect_chat(bot: Bot, update: Update, args: List[str]):

    chat = update.effective_chat
    user = update.effective_user

    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return

    if update.effective_chat.type == 'private':
        if len(args) >= 1:
            try:
                connect_chat = int(args[0])
                getstatusadmin = bot.get_chat_member(connect_chat, update.effective_message.from_user.id)
            except ValueError:
                try:
                    connect_chat = str(args[0])
                    get_chat = bot.getChat(connect_chat)
                    connect_chat = get_chat.id
                    getstatusadmin = bot.get_chat_member(connect_chat, update.effective_message.from_user.id)
                except BadRequest:
                    send_message(update.effective_message, "Zəhmət olmasa Sohbet ID-nizi yoxlayın!")
                    return
            except BadRequest:
                send_message(update.effective_message, "Zəhmət olmasa Sohbet ID-nizi yoxlayın!")
                return

            isadmin = getstatusadmin.status in ('administrator', 'creator')
            ismember = getstatusadmin.status in ('member')
            isallow = sql.allow_connect_to_chat(connect_chat)

            if (isadmin) or (isallow and ismember) or (user.id in SUDO_USERS) or (user.id in DEV_USERS):
                connection_status = sql.connect(update.effective_message.from_user.id, connect_chat)
                if connection_status:
                    conn_chat = dispatcher.bot.getChat(connected(bot, update, chat, user.id, need_admin=False))
                    chat_name = conn_chat.title
                    send_message(update.effective_message, "*{}* İlə uğurla əlaqələndirildi. Mövcud əmrləri görmək üçün /connection istifadə edin.".format(chat_name), parse_mode=ParseMode.MARKDOWN)
                    sql.add_history_conn(user.id, str(conn_chat.id), chat_name)
                else:
                    send_message(update.effective_message, "_Bağlantı alınmadı!_")
            else:
                send_message(update.effective_message, "Bu söhbətə qoşulmağa icazə verilmir!")
        else:
            gethistory = sql.get_history_conn(user.id)
            if gethistory:
                buttons = [
                    InlineKeyboardButton(text="✖️ Düyməni bağlayın", callback_data="connect_close"),
                    InlineKeyboardButton(text="🧹 Tarixçəni silin", callback_data="connect_clear")
                ]
            else:
                buttons = []
            conn = connected(bot, update, chat, user.id, need_admin=False)
            if conn:
                connectedchat = dispatcher.bot.getChat(conn)
                text = "_*{}* İlə əlaqə qurdunuz (`{}`)_".format(connectedchat.title, conn)
                buttons.append(InlineKeyboardButton(text="🔌 Ayırın", callback_data="connect_disconnect"))
            else:
                text = "_Qoşulmaq üçün söhbət ID-sini və ya etiketi yazın!_"
            if gethistory:
                text += "\n\n*Connection History:*\n"
                text += "╒═══「 *Məlumat* 」\n"
                text += "│  Çeşidləndi: Ən yeni`\n"
                text += "│\n"
                buttons = [buttons]
                for x in sorted(gethistory.keys(), reverse=True):
                    htime = time.strftime("%d/%m/%Y", time.localtime(x))
                    text += "╞═「 *{}* 」\n│   `{}`\n│   `{}`\n".format(gethistory[x]['chat_name'], gethistory[x]['chat_id'], htime)
                    text += "│\n"
                    buttons.append([InlineKeyboardButton(text=gethistory[x]['chat_name'], callback_data="connect({})".format(gethistory[x]['chat_id']))])
                text += "╘══「 Cəmi {} söhbət 」".format(str(len(gethistory)) + " (max)" if len(gethistory) == 5 else str(len(gethistory)))
                conn_hist = InlineKeyboardMarkup(buttons)
            elif buttons:
                conn_hist = InlineKeyboardMarkup([buttons])
            else:
                conn_hist = None
            send_message(update.effective_message, text, parse_mode="markdown", reply_markup=conn_hist)

    else:
        getstatusadmin = bot.get_chat_member(chat.id, update.effective_message.from_user.id)
        isadmin = getstatusadmin.status in ('administrator', 'creator')
        ismember = getstatusadmin.status in ('member')
        isallow = sql.allow_connect_to_chat(chat.id)
        if (isadmin) or (isallow and ismember) or (user.id in SUDO_USERS) or (user.id in DEV_USERS):
            connection_status = sql.connect(update.effective_message.from_user.id, chat.id)
            if connection_status:
                chat_name = dispatcher.bot.getChat(chat.id).title
                send_message(update.effective_message, "Uğurla əlaqələndirildi ==> *{}*".format(chat_name), parse_mode=ParseMode.MARKDOWN)
                try:
                    sql.add_history_conn(user.id, str(chat.id), chat_name)
                    bot.send_message(update.effective_message.from_user.id, "*{}* İlə əlaqə qurdunuz. Mövcud əmrləri görmək üçün /connection istifadə edin.".format(chat_name), parse_mode="markdown")
                except BadRequest:
                    pass
                except Unauthorized:
                    pass
            else:
                send_message(update.effective_message, "Bağlantı alınmadı!")
        else:
            send_message(update.effective_message, "Bu söhbətə qoşulmağa icazə verilmir!")


def disconnect_chat(bot: Bot, update: Update):

    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return

    if update.effective_chat.type == 'private':
        disconnection_status = sql.disconnect(update.effective_message.from_user.id)
        if disconnection_status:
           sql.disconnected_chat = send_message(update.effective_message, "Bu söhbətdən müvəffəqiyyətlə ayrıldı!")
        else:
           send_message(update.effective_message, "Bağlı deyilsiniz!")
    else:
        send_message(update.effective_message, "Bu əmr yalnız PM-də mövcuddur.")


def connected(bot, update, chat, user_id, need_admin=True):

    user = update.effective_user
    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)

    if spam == True:
        return
        
    if chat.type == chat.PRIVATE and sql.get_connected_chat(user_id):

        conn_id = sql.get_connected_chat(user_id).chat_id
        getstatusadmin = bot.get_chat_member(conn_id, update.effective_message.from_user.id)
        isadmin = getstatusadmin.status in ('administrator', 'creator')
        ismember = getstatusadmin.status in ('member')
        isallow = sql.allow_connect_to_chat(conn_id)

        if (isadmin) or (isallow and ismember) or (user.id in SUDO_USERS) or (user.id in DEV_USERS):
            if need_admin == True:
                if getstatusadmin.status in ('administrator', 'creator') or user_id in SUDO_USERS or user.id in DEV_USERS:
                    return conn_id
                else:
                    send_message(update.effective_message, "Bağlı qrupda bir admin olmalısınız!")
                    raise Exception("Not admin!")
            else:
                return conn_id
        else:
            send_message(update.effective_message, "Qrup əlaqə hüquqlarını dəyişdirdi, yada artıq idarəçi deyilsiniz.\nSizlə əlaqəni kəsdim.")
            disconnect_chat(bot, update)
            raise Exception("Not admin!")
    else:
        return False


@run_async
def help_connect_chat(bot: Bot, update: Update):

    spam = spamfilters(update.effective_message.text, update.effective_message.from_user.id, update.effective_chat.id)
    if spam == True:
        return

    if update.effective_message.chat.type != "private":
        send_message(update.effective_message, "Kömək almaq üçün bu əmrlə mənə PM də yazın.")
        return
    else:
        send_message(update.effective_message, "Bütün əmrlər", parse_mode="markdown")


@run_async
def connect_button(bot: Bot, update: Update):

    query = update.callback_query
    chat = update.effective_chat
    user = update.effective_user

    connect_match = re.match(r"Bağlanmtı\((.+?)\)", query.data)
    disconnect_match = query.data == "connect_disconnect"
    clear_match = query.data == "connect_clear"
    connect_close = query.data == "connect_close"

    if connect_match:
        target_chat = connect_match.group(1)
        getstatusadmin = bot.get_chat_member(target_chat, query.from_user.id)
        isadmin = getstatusadmin.status in ('administrator', 'creator')
        ismember = getstatusadmin.status in ('member')
        isallow = sql.allow_connect_to_chat(target_chat)

        if (isadmin) or (isallow and ismember) or (user.id in SUDO_USERS) or (user.id in DEV_USERS):
            connection_status = sql.connect(query.from_user.id, target_chat)

            if connection_status:
                conn_chat = dispatcher.bot.getChat(connected(bot, update, chat, user.id, need_admin=False))
                chat_name = conn_chat.title
                query.message.edit_text("*{}* İlə uğurla əlaqələndirildi. Mövcud əmrləri görmək üçün /connection istifadə edin.".format(chat_name), parse_mode=ParseMode.MARKDOWN)
                sql.add_history_conn(user.id, str(conn_chat.id), chat_name)
            else:
                query.message.edit_text("Bağlantı alınmadı!")
        else:
            bot.answer_callback_query(query.id, "Bu söhbətə qoşulmağa icazə verilmir!", show_alert=True)
    elif disconnect_match:
        disconnection_status = sql.disconnect(query.from_user.id)
        if disconnection_status:
           sql.disconnected_chat = query.message.edit_text("Çat əlaqəsi kəsildi!")
        else:
           bot.answer_callback_query(query.id, "Bağlı deyilsiniz!", show_alert=True)
    elif clear_match:
        sql.clear_history_conn(query.from_user.id)
        query.message.edit_text("Bağlı tarix silindi!")
    elif connect_close:
        query.message.edit_text("Bağlandı.\nTəkrar açmaq üçün /connect yazın")
    else:
        connect_chat(bot, update, [])

__help__ = """
 • /connect: söhbətə qoşulun (Bir qrupda PM-də /connect və ya /connect <qrup idsi> tərəfindən edilə bilər)
 • /connection: əlaqəli söhbətlərin siyahısı
 • /disconnect: söhbətdən ayrılın
 • /helpconnect: uzaqdan edilə bilən əmrləri sadalayın

*Admin only:*
 • /allowconnect <yes/no>: bir istifadəçinin söhbətə qoşulmasına icazə verin
"""

CONNECT_CHAT_HANDLER = CommandHandler("connect", connect_chat, pass_args=True)
CONNECTION_CHAT_HANDLER = CommandHandler("connection", connection_chat)
DISCONNECT_CHAT_HANDLER = CommandHandler("disconnect", disconnect_chat)
ALLOW_CONNECTIONS_HANDLER = CommandHandler("allowconnect", allow_connections, pass_args=True)
HELP_CONNECT_CHAT_HANDLER = CommandHandler("helpconnect", help_connect_chat)
CONNECT_BTN_HANDLER = CallbackQueryHandler(connect_button, pattern=r"connect")

dispatcher.add_handler(CONNECT_CHAT_HANDLER)
dispatcher.add_handler(CONNECTION_CHAT_HANDLER)
dispatcher.add_handler(DISCONNECT_CHAT_HANDLER)
dispatcher.add_handler(ALLOW_CONNECTIONS_HANDLER)
dispatcher.add_handler(HELP_CONNECT_CHAT_HANDLER)
dispatcher.add_handler(CONNECT_BTN_HANDLER)

__mod_name__ = "Bağlanma"
__handlers__ = [CONNECT_CHAT_HANDLER, CONNECTION_CHAT_HANDLER, DISCONNECT_CHAT_HANDLER, ALLOW_CONNECTIONS_HANDLER, HELP_CONNECT_CHAT_HANDLER, CONNECT_BTN_HANDLER]
