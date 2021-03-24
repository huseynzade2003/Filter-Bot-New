import html
import json
import html
import os
from typing import List, Optional

from telegram import Bot, Update, ParseMode, TelegramError
from telegram.ext import CommandHandler, run_async
from telegram.utils.helpers import mention_html

from bot import dispatcher, WHITELIST_USERS, SUPPORT_USERS, SUDO_USERS, DEV_USERS, OWNER_ID
from bot.modules.helper_funcs.chat_status import whitelist_plus, dev_plus
from bot.modules.helper_funcs.extraction import extract_user
from bot.modules.log_channel import gloggable

ELEVATED_USERS_FILE = os.path.join(os.getcwd(), 'bot/elevated_users.json')


def check_user_id(user_id: int, bot: Bot) -> Optional[str]:
    if not user_id:
        reply = "Bu ... söhbətdir!"

    elif user_id == bot.id:
        reply = "Bu o şəkildə işləmir."

    else:
        reply = None
    return reply


@run_async
@dev_plus
@gloggable
def addsudo(bot: Bot, update: Update, args: List[str]) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)
    rt = ""

    reply = check_user_id(user_id, bot)
    if reply:
        message.reply_text(reply)
        return ""

    with open(ELEVATED_USERS_FILE, 'r') as infile:
        data = json.load(infile)

    if user_id in SUDO_USERS:
        message.reply_text("Bu üzv onsuz da mənim SUDO-mdur.")
        return ""

    if user_id in SUPPORT_USERS:
        rt += "Bu istifadəçi artıq bir DƏSTƏK İSTİFADƏÇİSİDİR."
        data['supports'].remove(user_id)
        SUPPORT_USERS.remove(user_id)

    if user_id in WHITELIST_USERS:
        rt += "Bu istifadəçi artıq WHITELIST istifadəçisidir."
        data['whitelists'].remove(user_id)
        WHITELIST_USERS.remove(user_id)

    data['sudos'].append(user_id)
    SUDO_USERS.append(user_id)

    with open(ELEVATED_USERS_FILE, 'w') as outfile:
        json.dump(data, outfile, indent=4)

    update.effective_message.reply_text(
        rt + "\nBu istifadəçi {} Sudo-ya uğurla əlavə edildi!".format(user_member.first_name))

    log_message = (f"#SUDO\n"
                   f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
                   f"<b>İstifadəçi:</b> {mention_html(user_member.id, user_member.first_name)}")

    if chat.type != 'private':
        log_message = f"<b>{html.escape(chat.title)}:</b>\n" + log_message

    return log_message


@run_async
@dev_plus
@gloggable
def addsupport(bot: Bot, update: Update, args: List[str]) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)
    rt = ""

    reply = check_user_id(user_id, bot)
    if reply:
        message.reply_text(reply)
        return ""

    with open(ELEVATED_USERS_FILE, 'r') as infile:
        data = json.load(infile)

    if user_id in SUDO_USERS:
        rt += "Bu SUDO-nun DƏSTƏK statusunu aşağı salma"
        data['sudos'].remove(user_id)
        SUDO_USERS.remove(user_id)

    if user_id in SUPPORT_USERS:
        message.reply_text("Bu istifadəçi artıq SUDO-dur.")
        return ""

    if user_id in WHITELIST_USERS:
        rt += "WHITELIST İSTİFADƏÇİSİNDƏN KULLANICI DƏSTƏK EDƏCƏK Fəlakət səviyyəsinin yüksəldilməsi"
        data['whitelists'].remove(user_id)
        WHITELIST_USERS.remove(user_id)

    data['supports'].append(user_id)
    SUPPORT_USERS.append(user_id)

    with open(ELEVATED_USERS_FILE, 'w') as outfile:
        json.dump(data, outfile, indent=4)

    update.effective_message.reply_text(rt + f"\n{user_member.first_name} bir dəstək istifadəçisi olaraq əlavə edildi!")

    log_message = (f"#SUPPORT\n"
                   f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
                   f"<b>İstifadəçi:</b> {mention_html(user_member.id, user_member.first_name)}")

    if chat.type != 'private':
        log_message = "<b>{html.escape(chat.title)}:</b>\n" + log_message

    return log_message


@run_async
@dev_plus
@gloggable
def addwhitelist(bot: Bot, update: Update, args: List[str]) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)
    rt = ""

    reply = check_user_id(user_id, bot)
    if reply:
        message.reply_text(reply)
        return ""

    with open(ELEVATED_USERS_FILE, 'r') as infile:
        data = json.load(infile)

    if user_id in SUDO_USERS:
        rt += "Bu üzv bir SUDO-dur, SUDO-ya enir."
        data['sudos'].remove(user_id)
        SUDO_USERS.remove(user_id)

    if user_id in SUPPORT_USERS:
        rt += "Bu istifadəçi artıq bir SUPPORTDUR, DƏSTƏK üçün aşağı"
        data['supports'].remove(user_id)
        SUPPORT_USERS.remove(user_id)

    if user_id in WHITELIST_USERS:
        message.reply_text("Bu istifadəçi artıq WHITELIST istifadəçisidir.")
        return ""

    data['whitelists'].append(user_id)
    WHITELIST_USERS.append(user_id)

    with open(ELEVATED_USERS_FILE, 'w') as outfile:
        json.dump(data, outfile, indent=4)

    update.effective_message.reply_text(
        rt + f"\n{user_member.first_name} uğurlu bir Siyahı İstifadəçisinə təqdim edildi!")

    log_message = (f"#WHITELIST\n"
                   f"<b>Admin:</b> {mention_html(user.id, user.first_name)} \n"
                   f"<b>İstifadəçi:</b> {mention_html(user_member.id, user_member.first_name)}")

    if chat.type != 'private':
        log_message = f"<b>{html.escape(chat.title)}:</b>\n" + log_message

    return log_message


@run_async
@dev_plus
@gloggable
def removesudo(bot: Bot, update: Update, args: List[str]) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)

    reply = check_user_id(user_id, bot)
    if reply:
        message.reply_text(reply)
        return ""

    with open(ELEVATED_USERS_FILE, 'r') as infile:
        data = json.load(infile)

    if user_id in SUDO_USERS:
        message.reply_text("Normal istifadəçiyə endirmə")
        SUDO_USERS.remove(user_id)
        data['sudos'].remove(user_id)

        with open(ELEVATED_USERS_FILE, 'w') as outfile:
            json.dump(data, outfile, indent=4)

        log_message = (f"#UNSUDO\n"
                       f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
                       f"<b>İstifadəçi:</b> {mention_html(user_member.id, user_member.first_name)}")

        if chat.type != 'private':
            log_message = "<b>{}:</b>\n".format(html.escape(chat.title)) + log_message

        return log_message

    else:
        message.reply_text("Bu istifadəçi sudo deyil!")
        return ""


@run_async
@dev_plus
@gloggable
def removesupport(bot: Bot, update: Update, args: List[str]) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)

    reply = check_user_id(user_id, bot)
    if reply:
        message.reply_text(reply)
        return ""

    with open(ELEVATED_USERS_FILE, 'r') as infile:
        data = json.load(infile)

    if user_id in SUPPORT_USERS:
        message.reply_text("Demoting to Civilian")
        SUPPORT_USERS.remove(user_id)
        data['supports'].remove(user_id)

        with open(ELEVATED_USERS_FILE, 'w') as outfile:
            json.dump(data, outfile, indent=4)

        log_message = (f"#UNSUPPORT\n"
                       f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
                       f"<b>İstifadəçi:</b> {mention_html(user_member.id, user_member.first_name)}")

        if chat.type != 'private':
            log_message = f"<b>{html.escape(chat.title)}:</b>\n" + log_message

        return log_message

    else:
        message.reply_text("Bu istifadəçi support deyil!")
        return ""


@run_async
@dev_plus
@gloggable
def removewhitelist(bot: Bot, update: Update, args: List[str]) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)

    reply = check_user_id(user_id, bot)
    if reply:
        message.reply_text(reply)
        return ""

    with open(ELEVATED_USERS_FILE, 'r') as infile:
        data = json.load(infile)

    if user_id in WHITELIST_USERS:
        message.reply_text("Normal istifadəçiyə endirmə")
        WHITELIST_USERS.remove(user_id)
        data['whitelists'].remove(user_id)

        with open(ELEVATED_USERS_FILE, 'w') as outfile:
            json.dump(data, outfile, indent=4)

        log_message = (f"#UNWHITELIST\n"
                       f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
                       f"<b>İstifadəçi:</b> {mention_html(user_member.id, user_member.first_name)}")

        if chat.type != 'private':
            log_message = f"<b>{html.escape(chat.title)}:</b>\n" + log_message

        return log_message
    else:
        message.reply_text("Bu istifadəçi ağ siyahıda deyil!")
        return ""


@run_async
@whitelist_plus
def whitelistlist(bot: Bot, update: Update):
    reply = "<b>Ağ siyahıdakı istifadəçilər🤍:</b>\n"
    for each_user in WHITELIST_USERS:
        user_id = int(each_user)
        try:
            user = bot.get_chat(user_id)

            reply += f"• {mention_html(user_id, user.first_name)}\n"
        except TelegramError:
            pass
    update.effective_message.reply_text(reply, parse_mode=ParseMode.HTML)


@run_async
@whitelist_plus
def supportlist(bot: Bot, update: Update):
    reply = "<b>Support Siyahısı🧡:</b>\n"
    for each_user in SUPPORT_USERS:
        user_id = int(each_user)
        try:
            user = bot.get_chat(user_id)
            reply += f"• {mention_html(user_id, user.first_name)}\n"
        except TelegramError:
            pass
    update.effective_message.reply_text(reply, parse_mode=ParseMode.HTML)


@run_async
@whitelist_plus
def sudolist(bot: Bot, update: Update):
    true_sudo = list(set(SUDO_USERS) - set(DEV_USERS))
    reply = "<b>Sudo siyahısı❤:</b>\n"
    for each_user in true_sudo:
        user_id = int(each_user)
        try:
            user = bot.get_chat(user_id)
            reply += f"• {mention_html(user_id, user.first_name)}\n"
        except TelegramError:
            pass
    update.effective_message.reply_text(reply, parse_mode=ParseMode.HTML)


@run_async
@whitelist_plus
def devlist(bot: Bot, update: Update):
    true_dev = list(set(DEV_USERS) - {OWNER_ID})
    reply = "<b>My Developer Siyahısı🤎:</b>\n"
    for each_user in true_dev:
        user_id = int(each_user)
        try:
            user = bot.get_chat(user_id)
            reply += f"• {mention_html(user_id, user.first_name)}\n"
        except TelegramError:
            pass
    update.effective_message.reply_text(reply, parse_mode=ParseMode.HTML)


__help__ = """
*Yalnız Bot Sahibi:*

 • /addsudo: istifadəçini Sudo İstifadəçisi səviyyəsinə yüksəldir
 • /removesudo: istifadəçini Sudo İstifadəçisindən aşağı salır

 • /addsupport: istifadəçini dəstəkləyən istifadəçiyə təqdim edir
 • /removesupport: istifadəçini dəstək istifadəçisindən aşağı salır

 • /addwhitelist: istifadəçini ağ siyahıya gətirir
 • /removewhitelist: istifadəçini Ağ Siyahı İstifadəçisindən aşağı salır
 
 *Bot Admin Lists:*
 • /whitelistlist - Ağ siyahıya alınan istifadəçiləri siyahıya alın.
 • /supportlist - Support istifadəçilərini siyahıya alın.
 • /sudolist - Sudo istifadəçilərini siyahıya alın.
 • /devlist - DEV istifadəçilərini siyahıya alın.
"""

SUDO_HANDLER = CommandHandler(("addsudo"), addsudo, pass_args=True)
SUPPORT_HANDLER = CommandHandler(("addsupport"), addsupport, pass_args=True)
WHITELIST_HANDLER = CommandHandler(("addwhitelist"), addwhitelist, pass_args=True)
UNSUDO_HANDLER = CommandHandler(("removesudo"), removesudo, pass_args=True)
UNSUPPORT_HANDLER = CommandHandler(("removesupport"), removesupport, pass_args=True)
UNWHITELIST_HANDLER = CommandHandler(("removewhitelist"), removewhitelist, pass_args=True)

WHITELISTLIST_HANDLER = CommandHandler(["whitelistlist"], whitelistlist)
SUPPORTLIST_HANDLER = CommandHandler(["supportlist"], supportlist)
SUDOLIST_HANDLER = CommandHandler(["sudolist"], sudolist)
DEVLIST_HANDLER = CommandHandler(["devlist"], devlist)

dispatcher.add_handler(SUDO_HANDLER)
dispatcher.add_handler(SUPPORT_HANDLER)
dispatcher.add_handler(WHITELIST_HANDLER)
dispatcher.add_handler(UNSUDO_HANDLER)
dispatcher.add_handler(UNSUPPORT_HANDLER)
dispatcher.add_handler(UNWHITELIST_HANDLER)

dispatcher.add_handler(WHITELISTLIST_HANDLER)
dispatcher.add_handler(SUPPORTLIST_HANDLER)
dispatcher.add_handler(SUDOLIST_HANDLER)
dispatcher.add_handler(DEVLIST_HANDLER)

__mod_name__ = "Admin"
__handlers__ = [SUDO_HANDLER, SUPPORT_HANDLER, WHITELIST_HANDLER,
                UNSUDO_HANDLER, UNSUPPORT_HANDLER, UNWHITELIST_HANDLER,
                WHITELISTLIST_HANDLER, SUPPORTLIST_HANDLER, SUDOLIST_HANDLER, DEVLIST_HANDLER]
