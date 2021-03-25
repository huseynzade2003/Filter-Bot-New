from typing import List, Optional

from telegram import Message, MessageEntity
from telegram.error import BadRequest

from bot import LOGGER
from bot.modules.users import get_user_id


def id_from_reply(message):
    prev_message = message.reply_to_message
    if not prev_message:
        return None, None
    user_id = prev_message.from_user.id
    res = message.text.split(None, 1)
    if len(res) < 2:
        return user_id, ""
    return user_id, res[1]


def extract_user(message: Message, args: List[str]) -> Optional[int]:
    return extract_user_and_text(message, args)[0]


def extract_user_and_text(message: Message, args: List[str]) -> (Optional[int], Optional[str]):
    prev_message = message.reply_to_message
    split_text = message.text.split(None, 1)

    if len(split_text) < 2:
        return id_from_reply(message)  # only option possible

    text_to_parse = split_text[1]

    text = ""

    entities = list(message.parse_entities([MessageEntity.TEXT_MENTION]))
    if len(entities) > 0:
        ent = entities[0]
    else:
        ent = None

    # if entity offset matches (komanda sonu/mətn başlanğıcı) then all good
    if entities and ent and ent.offset == len(message.text) - len(text_to_parse):
        ent = entities[0]
        user_id = ent.user.id
        text = message.text[ent.offset + ent.length:]

    elif len(args) >= 1 and args[0][0] == '@':
        user = args[0]
        user_id = get_user_id(user)
        if not user_id:
            message.reply_text("Bu istifadəçinin kim olduğu barədə heç bir məlumat yoxdur. Onlarla əlaqə qura biləcəksiniz "
                               "bunun əvəzinə həmin şəxsin mesajına cavab verirsiniz və ya həmin istifadəçinin mesajlarından birini ötürürsünüz.")
            return None, None

        else:
            user_id = user_id
            res = message.text.split(None, 2)
            if len(res) >= 3:
                text = res[2]

    elif len(args) >= 1 and args[0].isdigit():
        user_id = int(args[0])
        res = message.text.split(None, 2)
        if len(res) >= 3:
            text = res[2]

    elif prev_message:
        user_id, text = id_from_reply(message)

    else:
        return None, None

    try:
        message.bot.get_chat(user_id)
    except BadRequest as excp:
        if excp.message in ("User_id_invalid", "Çat tapılmadı"):
            message.reply_text("Görünür əvvəllər bu istifadəçi ilə əlaqə qurmamışam - xahiş edirəm bir mesaj göndərin "
                               "mənə nəzarəti versinlər! (vudu kuklası kimi, bacarmaq üçün onlardan bir parça lazımdır) "
                               "müəyyən əmrləri yerinə yetirmək...)")
        else:
            LOGGER.exception("İstisna %s istifadəçi üzərində %s", excp.message, user_id)

        return None, None

    return user_id, text


def extract_text(message) -> str:
    return message.text or message.caption or (message.sticker.emoji if message.sticker else None)


def extract_unt_fedban(message: Message, args: List[str]) -> (Optional[int], Optional[str]):
    prev_message = message.reply_to_message
    split_text = message.text.split(None, 1)
    
    if len(split_text) < 2:
        return id_from_reply(message)  # only option possible
    
    text_to_parse = split_text[1]

    text = ""

    entities = list(message.parse_entities([MessageEntity.TEXT_MENTION]))
    if len(entities) > 0:
        ent = entities[0]
    else:
        ent = None
        
    # if entity offset matches (komanda sonu/mətn başlanğıcı) then all good
    if entities and ent and ent.offset == len(message.text) - len(text_to_parse):
        ent = entities[0]
        user_id = ent.user.id
        text = message.text[ent.offset + ent.length:]

    elif len(args) >= 1 and args[0][0] == '@':
        user = args[0]
        user_id = get_user_id(user)
        if not user_id and not str(user_id).isdigit():
            message.reply_text("Görünür əvvəllər bu istifadəçi ilə əlaqə qurmamışam - xahiş edirəm bir mesaj göndərin "
                               "mənə nəzarəti versinlər! (vudu kuklası kimi, bacarmaq üçün onlardan bir parça lazımdır) "
                               "müəyyən əmrləri yerinə yetirmək...)")
            return None, None

        else:
            user_id = user_id
            res = message.text.split(None, 2)
            if len(res) >= 3:
                text = res[2]

    elif len(args) >= 1 and args[0].isdigit():
        user_id = int(args[0])
        res = message.text.split(None, 2)
        if len(res) >= 3:
            text = res[2]

    elif prev_message:
        user_id, text = id_from_reply(message)

    else:
        return None, None

    try:
        message.bot.get_chat(user_id)
    except BadRequest as excp:
        if excp.message in ("User_id_invalid", "Çat tapılmadı") and not str(user_id).isdigit():
            message.reply_text("Bu istifadəçi ilə əvvəllər qarşılıqlı əlaqədə olmadığımı düşünürəm - xahiş edirəm mesaj göndərin"
                               "mənə nəzarəti versinlər! (Vudu kuklası kimi, bacarmaq üçün bir parçaya ehtiyacım var"
                               "müəyyən əmrləri yerinə yetirmək ...)")
            return None, None
        elif excp.message != "Chat not found":
            LOGGER.exception("Istifadəçi %s istisna %s", excp.message, user_id)
            return None, None
        elif not str(user_id).isdigit():
            return None, None

    return user_id, text


def extract_user_fban(message: Message, args: List[str]) -> Optional[int]:
    return extract_unt_fedban(message, args)[0]
