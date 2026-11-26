# © VEGA — Intellectual Property Rights

# Respect for Copyright and Content Protection

# In this project, we are committed to respecting community laws, protecting intellectual property rights, and appreciating the efforts of all creators and content owners.

# "All rights are reserved to their original owners, and this project does not constitute a waiver of any intellectual property rights belonging to other parties.

# © VEGA — All rights related to this project are reserved to their owners."

# Supporting Creators is a Responsibility

# - Creativity is the fruit of effort that deserves appreciation and respect.
# - Protecting copyright contributes to building a more just digital community.
# - Usage licenses and redistribution terms must be respected.
# - We reject unauthorized use of any content protected by copyright.

# Responsible Use Pledge

# By using this project, you pledge to respect intellectual property rights and not to copy or redistribute any protected content without obtaining the necessary permission or license.

# Be a partner in protecting creativity, and do not be a cause of rights violations.

# © VEGA | By: @TopVeGa All Rights Reserved



import re
import logging
import telebot
from telebot import types
from telebot.util import quick_markup

import config
import database as db
import utils

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(config.BOT_TOKEN)
db.init_db()

EMAIL_RE = re.compile(r"^[a-zA-Z0-9]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")


def is_dev(uid):
    return uid in config.dev


def escape_md(s):
    return re.sub(r'([_*\[\]()~`>#+\-=|{}.!\\])', r'\\\1', s)


@bot.message_handler(commands=["start", "restart"])
def cmd_start(message):
    db.create_or_update_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    if db.is_blocked(message.from_user.id):
        bot.reply_to(message, "تم حظرك من استخدام البوت.")
        return

    sub = db.get_active_subscription(message.from_user.id)
    sub_text = f"مشترك حتى: {sub['expires_at']}" if sub else f"مجاني (حد {config.FREE_EMAIL_LIMIT} بريد)"

    markup = quick_markup({
        "بريد جديد": {"callback_data": "NewEmail"},
        "قائمة بريدي": {"callback_data": "EmailList"},
        "حذف بريد": {"callback_data": "DelMenu"},
        "صندوق الوارد": {"callback_data": "InboxMenu"},
        "فحص بريد": {"callback_data": "CheckEmail"},
        "إعدادات البريد": {"callback_data": "SettingsMenu"},
        "الاشتراك": {"callback_data": "SubscribeMenu"},
    }, row_width=2)

    bot.send_message(
        message.chat.id,
        f"مرحباً {message.from_user.first_name}!\n{sub_text}\n\nاختر من القائمة:",
        reply_markup=markup
    )

    if is_dev(message.from_user.id):
        dev_kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        dev_kb.add(
            types.KeyboardButton("المستخدمون"),
            types.KeyboardButton("إحصائيات"),
            types.KeyboardButton("تصدير مستخدمين (TXT)"),
            types.KeyboardButton("استيراد مستخدمين (TXT)"),
            types.KeyboardButton("تصدير إيميلات (JSON)"),
            types.KeyboardButton("استيراد إيميلات (JSON)"),
            types.KeyboardButton("تفعيل التواصل"),
            types.KeyboardButton("تعطيل التواصل"),
            types.KeyboardButton("إخفاء لوحة الأدمن"),
        )
        bot.send_message(
            message.chat.id,
            "لوحة الإدارة (مرئية لك فقط):",
            reply_markup=dev_kb
        )

    try:
        _boxes = db.get_user_mailboxes(message.from_user.id)
        _notify_dev_on_start(message.from_user, sub, len(_boxes), _boxes)
    except Exception as e:
        logger.error(f"cmd_start notify: {e}")


@bot.message_handler(commands=["mail"])
def cmd_mail(message):
    if message.chat.type != "private":
        bot.reply_to(message, "هذا الأمر متاح فقط في الدردشة الخاصة.")
        return
    if db.is_blocked(message.from_user.id):
        bot.reply_to(message, "تم حظرك.")
        return
    db.create_or_update_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    cmd_start(message)


def _notify_dev_on_start(user, sub, boxes_count, box_list):
    logo = "جديد" if not sub else "مستخدم"
    username = f"@{user.username}" if user.username else "—"
    plan = "مجاني"
    expires = "—"
    if sub:
        plan = sub['plan']
        expires = sub["expires_at"]

    header = (
        f"<b>مستخدم دخل البوت</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"الاسم: <b>{user.first_name or '—'}</b>\n"
        f"المعرف: {username}\n"
        f"الآيدي: <code>{user.id}</code>\n"
    )

    if box_list:
        mails_txt = "\n".join(f"  • <code>{b['address']}</code>" for b in box_list[:10])
        if len(box_list) > 10:
            mails_txt += f"\n  … +{len(box_list) - 10} أخرى"
    else:
        mails_txt = "  — لا يوجد"

    body = (
        f"عدد البريد: <b>{boxes_count}</b>\n"
        f"البريد:\n{mails_txt}\n"
        f"الخطة: <b>{plan}</b>\n"
        f"الانتهاء: <code>{expires}</code>"
    )

    text = header + body

    for dev_id in config.dev:
        try:
            bot.send_message(dev_id, text, parse_mode="HTML")
        except Exception as e:
            logger.error(f"notify_dev_on_start -> {dev_id}: {e}")


dev_BTN_USERS = "المستخدمون"
dev_BTN_STATS = "إحصائيات"
dev_BTN_EXPORT_USERS = "تصدير مستخدمين (TXT)"
dev_BTN_IMPORT_USERS = "استيراد مستخدمين (TXT)"
dev_BTN_EXPORT_EMAILS = "تصدير إيميلات (JSON)"
dev_BTN_IMPORT_EMAILS = "استيراد إيميلات (JSON)"
dev_BTN_CONTACT_ON = "تفعيل التواصل"
dev_BTN_CONTACT_OFF = "تعطيل التواصل"
dev_BTN_HIDE = "إخفاء لوحة الأدمن"

dev_BUTTONS = {
    dev_BTN_USERS, dev_BTN_STATS,
    dev_BTN_EXPORT_USERS, dev_BTN_IMPORT_USERS,
    dev_BTN_EXPORT_EMAILS, dev_BTN_IMPORT_EMAILS,
    dev_BTN_CONTACT_ON, dev_BTN_CONTACT_OFF,
    dev_BTN_HIDE,
}


@bot.message_handler(func=lambda m: is_dev(m.from_user.id) and m.text in dev_BUTTONS)
def dev_reply_handler(message):
    text = message.text

    if text == dev_BTN_HIDE:
        bot.send_message(
            message.chat.id,
            "تم إخفاء لوحة الأدمن. استخدم /start لإظهارها مرة أخرى.",
            reply_markup=types.ReplyKeyboardRemove()
        )
        return

    if text == dev_BTN_USERS:
        users = db.get_all_users()
        if not users:
            bot.reply_to(message, "لا يوجد مستخدمون.")
            return
        lines = [f"{u['user_id']} | @{u['username'] or '-'} | {u['first_name'] or '-'} | {u['registered_at']}" for u in users[:50]]
        bot.reply_to(message, "آخر 50 مستخدم:\n\n" + "\n".join(lines))

    elif text == dev_BTN_STATS:
        s = db.get_stats()
        bot.reply_to(message, f"المستخدمون: {s['users']}\nالصناديق: {s['mailboxes']}\nالاشتراكات: {s['active_subs']}")

    elif text == dev_BTN_EXPORT_USERS:
        content = db.export_users_txt()
        bot.send_document(message.chat.id, ("users_export.txt", content.encode("utf-8")))

    elif text == dev_BTN_EXPORT_EMAILS:
        content = db.export_emails_json()
        bot.send_document(message.chat.id, ("emails_export.json", content.encode("utf-8")))

    elif text == dev_BTN_IMPORT_USERS:
        db.set_admin_pending(message.from_user.id, "import_users")
        bot.reply_to(message, "أرسل الآن ملف TXT للاستيراد.\nالصيغة: user_id|username|first_name|registered_at\n\n(أرسل /cancel للإلغاء)")

    elif text == dev_BTN_IMPORT_EMAILS:
        db.set_admin_pending(message.from_user.id, "import_emails")
        bot.reply_to(message, "أرسل الآن ملف JSON للإيميلات.\n\n(أرسل /cancel للإلغاء)")

    elif text == dev_BTN_CONTACT_ON:
        db.set_contact_enabled(True)
        bot.reply_to(message, "تم تفعيل التواصل: رسائل المستخدمين ستصل إليك.")

    elif text == dev_BTN_CONTACT_OFF:
        db.set_contact_enabled(False)
        bot.reply_to(message, "تم تعطيل التواصل: لن تصلك رسائل المستخدمين.")


@bot.message_handler(commands=["dev"])
def cmd_dev(message):
    if not is_dev(message.from_user.id):
        return
    dev_kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    dev_kb.add(
        types.KeyboardButton(dev_BTN_USERS),
        types.KeyboardButton(dev_BTN_STATS),
        types.KeyboardButton(dev_BTN_EXPORT_USERS),
        types.KeyboardButton(dev_BTN_IMPORT_USERS),
        types.KeyboardButton(dev_BTN_EXPORT_EMAILS),
        types.KeyboardButton(dev_BTN_IMPORT_EMAILS),
        types.KeyboardButton(dev_BTN_CONTACT_ON),
        types.KeyboardButton(dev_BTN_CONTACT_OFF),
        types.KeyboardButton(dev_BTN_HIDE),
    )
    bot.send_message(message.chat.id, "لوحة الإدارة:", reply_markup=dev_kb)


@bot.message_handler(
    func=lambda m: is_dev(m.from_user.id) and db.get_admin_pending(m.from_user.id) != "",
    content_types=["document", "text"]
)
def dev_import_handler(message):
    pending = db.get_admin_pending(message.from_user.id)

    if message.text and message.text.strip() == "/cancel":
        db.clear_admin_pending(message.from_user.id)
        bot.reply_to(message, "تم الإلغاء.")
        return

    if not message.document:
        bot.reply_to(message, "أرسل ملفاً (وليس نصاً). أو /cancel للإلغاء.")
        return

    try:
        info = bot.get_file(message.document.file_id)
        content = bot.download_file(info.file_path).decode("utf-8")
    except Exception as e:
        bot.reply_to(message, f"تعذر تنزيل الملف: {e}")
        return

    if pending == "import_users":
        count = db.import_users_txt(content)
        bot.reply_to(message, f"تم استيراد {count} مستخدم.")
    elif pending == "import_emails":
        count = db.import_emails_json(content)
        bot.reply_to(message, f"تم استيراد {count} صندوق بريد.")
    else:
        bot.reply_to(message, "لا توجد عملية استيراد معلّقة.")

    db.clear_admin_pending(message.from_user.id)


@bot.message_handler(
    func=lambda m: m.chat.type == "private"
    and m.from_user.id not in config.dev
    and db.get_contact_enabled()
    and not (m.text or "").startswith("/"),
    content_types=[
        "text", "photo", "video", "document", "audio", "voice",
        "sticker", "animation", "contact", "location", "video_note"
    ],
)
def contact_forward_handler(message):
    uid = message.from_user.id
    if db.is_blocked(uid):
        return

    user = db.get_user(uid)
    uname = f"@{user['username']}" if user and user["username"] else "—"
    header = (
        f"<b>رسالة من مستخدم</b>\n"
        f"{message.from_user.first_name or '—'} | {uname}\n"
        f"<code>{uid}</code>\n"
        f"للرد: قم بالرد على هذه الرسالة"
    )

    for dev_id in config.dev:
        try:
            bot.send_message(dev_id, header, parse_mode="HTML")
            copied = bot.forward_message(dev_id, message.chat.id, message.message_id)
            db.save_contact_map(copied.message_id, uid)
        except Exception as e:
            logger.error(f"contact_forward -> {dev_id}: {e}")


@bot.message_handler(
    func=lambda m: m.chat.type == "private"
    and m.from_user.id in config.dev
    and m.reply_to_message is not None
    and db.get_contact_user(m.reply_to_message.message_id) is not None,
    content_types=[
        "text", "photo", "video", "document", "audio", "voice",
        "sticker", "animation", "contact", "location", "video_note"
    ],
)
def dev_reply_contact_handler(message):
    target_uid = db.get_contact_user(message.reply_to_message.message_id)
    if not target_uid:
        return

    try:
        bot.copy_message(
            chat_id=target_uid,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
        )
        bot.reply_to(message, "تم إرسال الرد إلى المستخدم.")
    except Exception as e:
        bot.reply_to(message, f"فشل الإرسال: {e}")


@bot.callback_query_handler(func=lambda call: True)
def on_callback(call):
    uid = call.from_user.id
    cid = call.message.chat.id
    mid = call.message.message_id

    if db.is_blocked(uid):
        bot.answer_callback_query(call.id, "أنت محظور.")
        return

    if call.data == "NewEmail":
        bot.answer_callback_query(call.id, "جاري الإنشاء...")
        msg = bot.send_message(cid, "جاري إنشاء البريد...")

        address, password, token, domain = utils.create_bot_email(uid)
        if not address:
            bot.edit_message_text(f"{escape_md(password)}", cid, msg.message_id, parse_mode="MarkdownV2")
            return

        text = (
            f"تم إنشاء البريد\n\n"
            f"`{escape_md(address)}`\n"
            f"||{escape_md(password)}||"
        )
        bot.edit_message_text(text, cid, msg.message_id, parse_mode="MarkdownV2")

    elif call.data == "EmailList":
        boxes = db.get_user_mailboxes(uid)
        if not boxes:
            bot.answer_callback_query(call.id, "ليس لديك بريد.", show_alert=True)
            return

        kb = []
        for b in boxes:
            cnt = utils.get_message_count(b["token"])
            status = "مفعل" if b["enabled"] else "معطل"
            label = f"{status} {b['address']} ({cnt if cnt >= 0 else '?'})"
            kb.append([types.InlineKeyboardButton(label, callback_data=f"MailInfo|{b['address']}")])
        kb.append([types.InlineKeyboardButton("إغلاق", callback_data="Close")])

        bot.send_message(cid, "قائمة بريدك:", reply_markup=types.InlineKeyboardMarkup(kb))
        bot.answer_callback_query(call.id)

    elif call.data.startswith("MailInfo|"):
        address = call.data.split("|", 1)[1]
        if not EMAIL_RE.match(address):
            bot.answer_callback_query(call.id, "بريد غير صالح.", show_alert=True)
            return
        b = db.get_mailbox_by_address(uid, address)
        if not b:
            bot.answer_callback_query(call.id, "البريد غير موجود.", show_alert=True)
            return
        cnt = utils.get_message_count(b["token"])
        text = (
            f"{b['address']}\n"
            f"{b['created_at']}\n"
            f"الرسائل: {cnt if cnt >= 0 else '?'}\n"
            f"الإشعارات: {'مفعّلة' if b['notifications_enabled'] else 'معطّلة'}\n"
            f"الحالة: {'مفعّل' if b['enabled'] else 'معطّل'}"
        )
        bot.answer_callback_query(call.id, text, show_alert=True)

    elif call.data == "DelMenu":
        boxes = db.get_user_mailboxes(uid)
        if not boxes:
            bot.answer_callback_query(call.id, "ليس لديك بريد.", show_alert=True)
            return
        kb = [[types.InlineKeyboardButton(b["address"], callback_data=f"DelAsk|{b['address']}")] for b in boxes]
        kb.append([
            types.InlineKeyboardButton("حذف الكل", callback_data="DelAllAsk"),
            types.InlineKeyboardButton("إغلاق", callback_data="Close"),
        ])
        bot.send_message(cid, "اختر بريداً للحذف:", reply_markup=types.InlineKeyboardMarkup(kb))
        bot.answer_callback_query(call.id)

    elif call.data.startswith("DelAsk|"):
        address = call.data.split("|", 1)[1]
        kb = [
            [types.InlineKeyboardButton("نعم، احذف", callback_data=f"DelYes|{address}")],
            [types.InlineKeyboardButton("إلغاء", callback_data="Close")],
        ]
        bot.send_message(cid, f"حذف {escape_md(address)}؟", parse_mode="MarkdownV2",
                         reply_markup=types.InlineKeyboardMarkup(kb))
        bot.answer_callback_query(call.id)

    elif call.data.startswith("DelYes|"):
        address = call.data.split("|", 1)[1]
        if not EMAIL_RE.match(address):
            bot.answer_callback_query(call.id, "بريد غير صالح.", show_alert=True)
            return
        b = db.get_mailbox_by_address(uid, address)
        if b and b["token"]:
            utils.delete_remote_account(b["token"])
        db.delete_mailbox(uid, address)
        bot.answer_callback_query(call.id, "تم الحذف.", show_alert=True)
        bot.delete_message(cid, mid)

    elif call.data == "DelAllAsk":
        kb = [
            [types.InlineKeyboardButton("نعم، احذف الكل", callback_data="DelAllYes")],
            [types.InlineKeyboardButton("إلغاء", callback_data="Close")],
        ]
        bot.send_message(cid, "حذف جميع صناديق البريد؟", reply_markup=types.InlineKeyboardMarkup(kb))
        bot.answer_callback_query(call.id)

    elif call.data == "DelAllYes":
        for b in db.get_user_mailboxes(uid):
            if b["token"]:
                utils.delete_remote_account(b["token"])
        db.delete_all_mailboxes(uid)
        bot.answer_callback_query(call.id, "تم حذف الكل.", show_alert=True)
        bot.delete_message(cid, mid)

    elif call.data == "InboxMenu":
        boxes = db.get_user_mailboxes(uid)
        if not boxes:
            bot.answer_callback_query(call.id, "ليس لديك بريد.", show_alert=True)
            return
        kb = [[types.InlineKeyboardButton(b["address"], callback_data=f"Inbox|{b['address']}")] for b in boxes]
        kb.append([types.InlineKeyboardButton("إغلاق", callback_data="Close")])
        bot.send_message(cid, "اختر بريداً لعرض الوارد:", reply_markup=types.InlineKeyboardMarkup(kb))
        bot.answer_callback_query(call.id)

    elif call.data.startswith("Inbox|"):
        address = call.data.split("|", 1)[1]
        if not EMAIL_RE.match(address):
            bot.answer_callback_query(call.id, "بريد غير صالح.", show_alert=True)
            return
        b = db.get_mailbox_by_address(uid, address)
        if not b:
            bot.answer_callback_query(call.id, "غير موجود.", show_alert=True)
            return
        if not b["enabled"]:
            bot.answer_callback_query(call.id, "هذا البريد معطّل.", show_alert=True)
            return

        bot.answer_callback_query(call.id, "جاري الجلب...")
        ok, res = utils.fetch_inbox(b["token"])
        if not ok:
            bot.send_message(cid, res)
            return
        bot.send_message(cid, f"وارد {address}:")
        for m in res[:5]:
            bot.send_message(cid, m[:4000], disable_web_page_preview=True)

    elif call.data == "CheckEmail":
        boxes = db.get_user_mailboxes(uid)
        if not boxes:
            bot.answer_callback_query(call.id, "ليس لديك بريد.", show_alert=True)
            return
        kb = [[types.InlineKeyboardButton(b["address"], callback_data=f"Check|{b['address']}")] for b in boxes]
        kb.append([types.InlineKeyboardButton("إغلاق", callback_data="Close")])
        bot.send_message(cid, "اختر بريداً لفحصه:", reply_markup=types.InlineKeyboardMarkup(kb))
        bot.answer_callback_query(call.id)

    elif call.data.startswith("Check|"):
        address = call.data.split("|", 1)[1]
        if not EMAIL_RE.match(address):
            bot.answer_callback_query(call.id, "بريد غير صالح.", show_alert=True)
            return
        b = db.get_mailbox_by_address(uid, address)
        if not b:
            bot.answer_callback_query(call.id, "غير موجود.", show_alert=True)
            return
        cnt = utils.get_message_count(b["token"])
        status = "مفعّل" if b["enabled"] else "معطّل"
        bot.answer_callback_query(
            call.id,
            f"{address}\nعدد الرسائل: {cnt if cnt >= 0 else '?'}\n{status}",
            show_alert=True
        )

    elif call.data == "SettingsMenu":
        boxes = db.get_user_mailboxes(uid)
        if not boxes:
            bot.answer_callback_query(call.id, "ليس لديك بريد.", show_alert=True)
            return
        kb = [[types.InlineKeyboardButton(b["address"], callback_data=f"SetPick|{b['address']}")] for b in boxes]
        kb.append([types.InlineKeyboardButton("إغلاق", callback_data="Close")])
        bot.send_message(cid, "اختر بريداً لإدارته:", reply_markup=types.InlineKeyboardMarkup(kb))
        bot.answer_callback_query(call.id)

    elif call.data.startswith("SetPick|"):
        address = call.data.split("|", 1)[1]
        if not EMAIL_RE.match(address):
            bot.answer_callback_query(call.id, "بريد غير صالح.", show_alert=True)
            return
        b = db.get_mailbox_by_address(uid, address)
        if not b:
            bot.answer_callback_query(call.id, "غير موجود.", show_alert=True)
            return
        kb = quick_markup({
            "تغيير كلمة المرور": {"callback_data": f"SetPwd|{address}"},
            "تغيير التوكن": {"callback_data": f"SetTok|{address}"},
            "تعيين صورة": {"callback_data": f"SetImg|{address}"},
            "الإشعارات": {"callback_data": f"SetNotify|{address}"},
            "تفعيل/تعطيل": {"callback_data": f"SetToggle|{address}"},
            "رجوع": {"callback_data": "SettingsMenu"},
        }, row_width=2)
        bot.send_message(cid, f"إعدادات {address}:", reply_markup=kb)
        bot.answer_callback_query(call.id)

    elif call.data.startswith("SetPwd|"):
        address = call.data.split("|", 1)[1]
        msg = bot.send_message(cid, "أرسل كلمة المرور الجديدة (6 أحرف على الأقل):")
        bot.register_next_step_handler(msg, _do_set_password, address)

    elif call.data.startswith("SetTok|"):
        address = call.data.split("|", 1)[1]
        msg = bot.send_message(cid, "أرسل التوكن الجديد (أو /cancel للإلغاء):")
        bot.register_next_step_handler(msg, _do_set_token, address)

    elif call.data.startswith("SetImg|"):
        address = call.data.split("|", 1)[1]
        msg = bot.send_message(cid, "أرسل صورة لتعيينها لهذا البريد:")
        bot.register_next_step_handler(msg, _do_set_avatar, address)

    elif call.data.startswith("SetNotify|"):
        address = call.data.split("|", 1)[1]
        b = db.get_mailbox_by_address(uid, address)
        if not b:
            bot.answer_callback_query(call.id, "غير موجود.", show_alert=True)
            return
        new_val = 0 if b["notifications_enabled"] else 1
        db.update_mailbox_field(uid, address, "notifications_enabled", new_val)
        bot.answer_callback_query(call.id, f"الإشعارات: {'مفعّلة' if new_val else 'معطّلة'}", show_alert=True)

    elif call.data.startswith("SetToggle|"):
        address = call.data.split("|", 1)[1]
        b = db.get_mailbox_by_address(uid, address)
        if not b:
            bot.answer_callback_query(call.id, "غير موجود.", show_alert=True)
            return
        new_val = 0 if b["enabled"] else 1
        db.update_mailbox_field(uid, address, "enabled", new_val)
        utils.set_account_enabled(b["token"], bool(new_val))
        bot.answer_callback_query(call.id, f"الحالة: {'مفعّل' if new_val else 'معطّل'}", show_alert=True)

    elif call.data == "SubscribeMenu":
        sub = db.get_active_subscription(uid)
        if sub:
            bot.send_message(cid, f"مشترك حتى {sub['expires_at']}")
            bot.answer_callback_query(call.id)
            return
        kb = quick_markup({
            "دفع بـ Stars": {"callback_data": "PayStars"},
            "دفع بـ TON": {"callback_data": "PayTON"},
            "رجوع": {"callback_data": "Close"},
        }, row_width=1)
        bot.send_message(
            cid,
            f"الاشتراك الشهري:\n{config.STARS_MONTHLY_PRICE} نجمة\n{config.TON_MONTHLY_PRICE_NANO / 1e9} TON",
            reply_markup=kb
        )
        bot.answer_callback_query(call.id)

    elif call.data == "PayStars":
        prices = [types.LabeledPrice(label="اشتراك شهري", amount=config.STARS_MONTHLY_PRICE)]
        bot.send_invoice(
            chat_id=cid,
            title="اشتراك شهري - bot Mail",
            description="بريد ورسائل غير محدودة",
            invoice_payload=f"sub_stars_{uid}",
            provider_token="",
            currency="XTR",
            prices=prices,
        )
        bot.answer_callback_query(call.id)

    elif call.data == "PayTON":
        comment = f"{config.TON_PAYMENT_COMMENT_PREFIX}{uid}"
        bot.answer_callback_query(call.id)
        bot.send_message(
            cid,
            f"أرسل **{config.TON_MONTHLY_PRICE_NANO / 1e9} TON** إلى:\n"
            f"`{config.TON_WALLET}`\n\n"
            f"**مع التعليق (إلزامي):**\n`{comment}`\n\n"
            f"التحقق التلقائي يتطلب ربط TON Center API. حالياً تواصل مع الإدارة بعد التحويل.",
            parse_mode="Markdown"
        )

    elif call.data == "Close":
        try:
            bot.delete_message(cid, mid)
        except Exception:
            pass
        bot.answer_callback_query(call.id)


def _do_set_password(message, address):
    uid = message.from_user.id
    pwd = message.text.strip() if message.text else ""
    if pwd == "/cancel":
        bot.reply_to(message, "تم الإلغاء.")
        return
    if len(pwd) < 6:
        bot.reply_to(message, "كلمة المرور قصيرة جداً (6 أحرف على الأقل).")
        return
    b = db.get_mailbox_by_address(uid, address)
    if not b:
        bot.reply_to(message, "البريد غير موجود.")
        return
    ok, info = utils.change_password(b["token"], pwd)
    if not ok:
        bot.reply_to(message, f"فشل تغيير كلمة المرور: {info[:200]}")
        return
    new_token, raw = utils.refresh_token(address, pwd)
    db.update_mailbox_field(uid, address, "password", pwd)
    if new_token:
        db.update_mailbox_field(uid, address, "token", new_token)
    bot.reply_to(message, "تم تغيير كلمة المرور بنجاح.")


def _do_set_token(message, address):
    uid = message.from_user.id
    tok = message.text.strip() if message.text else ""
    if tok == "/cancel":
        bot.reply_to(message, "تم الإلغاء.")
        return
    if len(tok) < 20:
        bot.reply_to(message, "التوكن غير صالح.")
        return
    db.update_mailbox_field(uid, address, "token", tok)
    bot.reply_to(message, "تم تحديث التوكن.")


def _do_set_avatar(message, address):
    uid = message.from_user.id
    if not message.photo:
        bot.reply_to(message, "أرسل صورة.")
        return
    file_id = message.photo[-1].file_id
    db.update_mailbox_field(uid, address, "avatar_file_id", file_id)
    bot.send_photo(message.chat.id, file_id, caption=f"تم تعيين الصورة لـ {address}")


@bot.pre_checkout_query_handler(func=lambda q: True)
def pre_checkout(query):
    bot.answer_pre_checkout_query(query.id, ok=True)


@bot.message_handler(content_types=["successful_payment"])
def on_payment(message):
    p = message.successful_payment
    db.create_subscription(message.from_user.id, "stars_monthly", 30, "stars", p.telegram_payment_charge_id)
    bot.send_message(message.chat.id, f"تم تفعيل الاشتراك 30 يوماً!\nمرجع: {p.telegram_payment_charge_id}")


@bot.message_handler(commands=["verify_ton"])
def verify_ton(message):
    uid = message.from_user.id
    comment = f"{config.TON_PAYMENT_COMMENT_PREFIX}{uid}"
    bot.reply_to(
        message,
        f"للتحقق من دفع TON:\n"
        f"المحفظة: `{config.TON_WALLET}`\n"
        f"المبلغ: {config.TON_MONTHLY_PRICE_NANO / 1e9} TON\n"
        f"التعليق: `{comment}`\n\n"
        f"تواصل مع الإدارة بعد التحويل للتحقق اليدوي.",
        parse_mode="Markdown"
    )


if __name__ == "__main__":
    print("البوت يعمل...")
    bot.infinity_polling(timeout=20, long_polling_timeout=10, skip_pending=True, none_stop=True)