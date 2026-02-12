#!/usr/bin/env python3
"""
Telegram Userbot — Keyword Monitor
===================================
يراقب كل الجروبات والقنوات اللي الحساب عضو فيها ويبعث تنبيه عند وجود كلمة مفتاحية.
التحكم عبر Saved Messages.
"""

import os
import re
import sys
import sqlite3
import logging
import asyncio
import subprocess
import shutil
from datetime import datetime

from dotenv import load_dotenv
from telethon import TelegramClient, events, errors
from telethon.tl.types import (
    PeerUser, PeerChannel, Channel, Chat, User,
    MessageMediaDocument, MessageMediaPhoto,
)

# ──────────────────────────── CONFIG ────────────────────────────

load_dotenv()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_NAME = "userbot_session"
DB_FILE = "keywords.db"
LOG_FILE = "bot.log"

if not API_ID or not API_HASH:
    print("❌  يجب تعيين API_ID و API_HASH في ملف .env")
    sys.exit(1)

API_ID = int(API_ID)

# ──────────────────────────── LOGGING ───────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("userbot")

# ──────────────────────────── DEFAULT KEYWORDS ──────────────────

DEFAULT_KEYWORDS = [
    "تعروفون احد يسوي",
    "تعرفون احد يحل",
    "تعرفون احد يطلع",
    "تعرفون حد يسوي",
    "تعرفون حد يساعندي",
    "تعرفون حد يحل",
    "تعرفون شخص يسوي",
    "تعرفون شخص يحل",
    "تعرفون شخص يطلع",
    "تعرفون ناس يسون",
    "تعرفون ناس تحل",
    "تعرفون ناس يحلون",
    "تعرفون ناس تطلع اعذار",
    "تعرفون ناس تطلع سكليف",
    "تعرفون ناس يطلعون اعذار",
    "تعرفون ناس يطلعون سكليف",
    "ابي احد يحل",
    "ابي احد يسوي",
    "ابي احد يساعدني",
    "ابي احد يطلع",
    "ابي احد يلخص",
    "ابي مساعده",
    "ابي مساعدة",
    "ابي احد يصمم",
    "عندكم احد يحل",
    "عندكم احد يسوي",
    "عندكم احد يطلع",
    "ابغى احد يحل",
    "ابغى احد يسوي",
    "ابغى احد يطلع",
    "ابغى احد يساعدني",
    "احد يحل واجب",
    "احد يسوي واجب",
    "احد يطلع سكليف",
    "احد يطلع اعذار",
    "ابغا احد يحل",
    "ابغا احد يسوي",
    "ابغا احد يطلع",
    "يحل كويز",
    "من يحل واجب",
    "من يسوي لي واجب",
    "من يسوي سكليف",
    "من يسوي تلخيص",
    "من يسوي بروزنتيشن",
    "من يسوي بوربوينت",
    "من يسوي تصميم",
    "من وين اجيب سكليف",
    "كيف اجيب سكليف",
    "كيف اخذ سكليف",
    "كيف اجيب عذر",
    "ابغى عذر",
    "ابغا حد يحل واجب",
    "ابي احد يحل لي واجب",
    "فيه احد يقدر يسوي عرض",
    "تعرفون احد يسوي برفريزنق",
    "تعرفون احد يطلع سكليف",
    "يساعدني",
    "السلام عليكم فيه احد يحل",
    "السلام عليكم فيه احد يسوي",
    "السلام عليكم فيه احد يطلع",
    "فيه احد يحل يساعدني",
    "احد يعرف مضمون يسوي اعذار",
    "تعرفون احد يسوي",
    "احتاج مساعده",
    "احتاج مساعدة",
    "ابغى مساعده",
    "ابغى مساعدة",
    "حد يعرف حد يحل",
    "حد يعرف حد يسوي",
    "حد يعرف حد يطلع",
    "حد يعرف حد يساعدني",
    "بنات اللي يسون سكسليقات ثقه ولا ابي سكليف",
    "ابي سكليف على تاريخ قديم في احد يسوي",
    "احد يسوي عروض تقديميه",
    "احد يسوي سكليف",
    "احد يسوي بحث",
    "احد يسوي عذر",
    "احد يسوي تقرير",
    "ابي عذر",
    "ابغا عذر",
    "احتاج عذر",
    "احتاج اعذار",
    "مين يحل كويز",
    "مين يحل واجب",
    "مين يحل واجبات",
    "مين يسوي واجب",
    "مين يسوي بحث",
    "مين يسوي تقرير",
    "مين يسوي عروض",
    "مين يسوي سكليف",
    "مين يطلع عذر",
    "مين يطلع اعذار",
    "مين يطلع سكليف",
    "مين يطلع اجازة مرضية",
    "فيه احد يطلع سكليف",
    "فيه احد يطلع اعذار",
    "فيه احد يطلع اجازة مرضية",
    "فيه احد يسوي واجب",
    "فيه احد يسوي واجبات",
    "فيه احد يسوي بحوث",
    "فيه احد يسوي بحث",
    "ابي رقم احد يسوي سكليف ثقه",
    "ابي رقم احد يسوي بحث",
    "ابي رقم احد يسوي واجبات",
    "ابي رقم احد يسوي اجازة مرضية",
    "ابي رقم احد يسوي عرض",
    "ابي رقم احد يسوي عروض",
    "ابي احد يسوي لي سكليف",
    "ابي احد يسوي لي تقرير",
    "ابي احد يسوي لي بحث",
    "تعرفون ناس يحلون واجبات",
    "تعرفون ناس يسون بحوث",
    "تعرفون ناس يسون عروض",
    "تعرفون ناس يسون اجازات مرضية",
    "ياخوان ابي حد يحل كويز فيزياء",
    "ابي حد يحل كويز",
    "السلام عليكم بغيت واحد يسوي لي ميرشنت",
    "بغيت واحد يسوي لي ميرشنت",
    "بغيت واحد يسوي لي واجب",
    "احد يعرف شخص يسوي خريطه ذهنيه",
    "احد يعرف شخص يسوي سكليف",
    "مين يعرف يحل انقليزي",
    "مين يعرف يحل واجب",
    "مين يعرف يسوي بحث",
    "ابي دكتور يحل لي",
    "ابي دكتور يسوي لي",
    "ابي دكتور يطلع لي",
    "من يعرف واحد يسوي",
]

# ──────────────────────────── DATABASE ──────────────────────────

def init_db():
    """إنشاء قاعدة البيانات والجدول إذا لم يكن موجوداً."""
    conn = sqlite3.connect(DB_FILE)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS keywords (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword  TEXT    NOT NULL UNIQUE,
            is_regex INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.commit()
    conn.close()
    # إضافة الكلمات الافتراضية لو القاعدة فاضية
    seed_defaults()


def seed_defaults():
    """إضافة الكلمات الافتراضية إذا كانت القاعدة فاضية."""
    conn = sqlite3.connect(DB_FILE)
    count = conn.execute("SELECT COUNT(*) FROM keywords").fetchone()[0]
    if count == 0:
        log.info(f"📥  إضافة {len(DEFAULT_KEYWORDS)} كلمة مفتاحية افتراضية...")
        for kw in DEFAULT_KEYWORDS:
            try:
                conn.execute(
                    "INSERT INTO keywords (keyword, is_regex) VALUES (?, 0)",
                    (kw,),
                )
            except sqlite3.IntegrityError:
                pass
        conn.commit()
        log.info("✅  تمت إضافة الكلمات الافتراضية بنجاح.")
    conn.close()


def get_keywords() -> list[dict]:
    """إرجاع كل الكلمات المفتاحية."""
    conn = sqlite3.connect(DB_FILE)
    rows = conn.execute("SELECT keyword, is_regex FROM keywords").fetchall()
    conn.close()
    return [{"keyword": r[0], "is_regex": bool(r[1])} for r in rows]


def add_keyword(keyword: str, is_regex: bool = False) -> bool:
    """إضافة كلمة مفتاحية. ترجع True لو نجحت."""
    conn = sqlite3.connect(DB_FILE)
    try:
        conn.execute(
            "INSERT INTO keywords (keyword, is_regex) VALUES (?, ?)",
            (keyword, int(is_regex)),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def del_keyword(keyword: str) -> bool:
    """حذف كلمة مفتاحية. ترجع True لو تم الحذف."""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.execute("DELETE FROM keywords WHERE keyword = ?", (keyword,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted

# ──────────────────────────── CLIPBOARD (TERMUX) ────────────────

def copy_to_clipboard(text: str):
    """نسخ النص للحافظة باستخدام termux-clipboard-set."""
    if shutil.which("termux-clipboard-set"):
        try:
            subprocess.run(
                ["termux-clipboard-set"],
                input=text.encode("utf-8"),
                timeout=5,
                check=True,
            )
            log.info("📋  تم نسخ التنبيه للحافظة.")
        except Exception as e:
            log.warning(f"⚠️  فشل النسخ للحافظة: {e}")
    else:
        log.debug("termux-clipboard-set غير متوفر — تم تخطي النسخ.")

# ──────────────────────────── HELPERS ───────────────────────────

def match_keywords(text: str, keywords: list[dict]) -> list[str]:
    """فحص النص مقابل الكلمات. ترجع قائمة بالكلمات المتطابقة."""
    matched = []
    for kw in keywords:
        try:
            if kw["is_regex"]:
                if re.search(kw["keyword"], text, re.IGNORECASE):
                    matched.append(kw["keyword"])
            else:
                if kw["keyword"].lower() in text.lower():
                    matched.append(kw["keyword"])
        except re.error:
            log.warning(f"⚠️  تعبير regex غير صالح: {kw['keyword']}")
    return matched


def build_message_link(chat, msg_id: int) -> str:
    """بناء رابط الرسالة."""
    if hasattr(chat, "username") and chat.username:
        return f"https://t.me/{chat.username}/{msg_id}"
    if hasattr(chat, "id"):
        # supergroup/channel خاص — internal id
        internal_id = chat.id
        return f"https://t.me/c/{internal_id}/{msg_id}"
    return ""


def get_sender_name(sender) -> str:
    """الحصول على اسم المرسل."""
    if sender is None:
        return "مجهول"
    if isinstance(sender, User):
        parts = []
        if sender.first_name:
            parts.append(sender.first_name)
        if sender.last_name:
            parts.append(sender.last_name)
        return " ".join(parts) if parts else "بدون اسم"
    if hasattr(sender, "title"):
        return sender.title
    return "مجهول"

# ──────────────────────────── BOT ───────────────────────────────

async def main():
    init_db()

    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    client.flood_sleep_threshold = 60  # تعامل تلقائي مع FloodWait حتى 60 ثانية

    await client.start()
    me = await client.get_me()
    owner_id = me.id
    log.info(f"✅  تم تسجيل الدخول: {me.first_name} (ID: {owner_id})")

    # حالة المراقبة
    monitoring = {"active": True}

    # ───────── أوامر Saved Messages ─────────

    @client.on(events.NewMessage(
        outgoing=True,
        from_users=owner_id,
        func=lambda e: e.is_private and e.text and e.text.startswith("/"),
    ))
    async def command_handler(event):
        # فقط في Saved Messages (المحادثة مع النفس)
        if event.chat_id != owner_id:
            return

        text = event.raw_text.strip()
        cmd_parts = text.split(maxsplit=1)
        cmd = cmd_parts[0].lower()
        arg = cmd_parts[1].strip() if len(cmd_parts) > 1 else ""

        # ── /add ──
        if cmd == "/add":
            if not arg:
                await event.reply("⚠️  الاستخدام: `/add كلمة`\nللريجكس: `/add r:pattern`")
                return
            is_regex = False
            keyword = arg
            if arg.startswith("r:"):
                is_regex = True
                keyword = arg[2:].strip()
                # تحقق من صحة الريجكس
                try:
                    re.compile(keyword)
                except re.error as e:
                    await event.reply(f"❌  تعبير regex غير صالح: `{e}`")
                    return
            if add_keyword(keyword, is_regex):
                kind = "regex" if is_regex else "كلمة"
                await event.reply(f"✅  تمت إضافة {kind}: **{keyword}**")
                log.info(f"➕  كلمة جديدة: {keyword} (regex={is_regex})")
            else:
                await event.reply(f"⚠️  الكلمة **{keyword}** موجودة بالفعل.")

        # ── /del ──
        elif cmd == "/del":
            if not arg:
                await event.reply("⚠️  الاستخدام: `/del كلمة`")
                return
            if del_keyword(arg):
                await event.reply(f"🗑  تم حذف: **{arg}**")
                log.info(f"➖  حذف كلمة: {arg}")
            else:
                await event.reply(f"⚠️  الكلمة **{arg}** غير موجودة.")

        # ── /list ──
        elif cmd == "/list":
            kws = get_keywords()
            if not kws:
                await event.reply("📭  لا توجد كلمات مفتاحية حالياً.")
            else:
                lines = []
                for i, kw in enumerate(kws, 1):
                    tag = " 🔤" if not kw["is_regex"] else " 🔣 regex"
                    lines.append(f"  {i}. `{kw['keyword']}`{tag}")
                header = f"📋  **الكلمات المفتاحية ({len(kws)}):**\n"
                await event.reply(header + "\n".join(lines))

        # ── /on ──
        elif cmd == "/on":
            monitoring["active"] = True
            await event.reply("▶️  تم تفعيل المراقبة.")
            log.info("▶️  المراقبة مفعّلة.")

        # ── /off ──
        elif cmd == "/off":
            monitoring["active"] = False
            await event.reply("⏸  تم إيقاف المراقبة.")
            log.info("⏸  المراقبة متوقفة.")

        # ── /help ──
        elif cmd == "/help":
            help_text = (
                "📖  **أوامر البوت:**\n\n"
                "`/add كلمة` — إضافة كلمة مفتاحية\n"
                "`/add r:pattern` — إضافة تعبير regex\n"
                "`/del كلمة` — حذف كلمة مفتاحية\n"
                "`/list` — عرض كل الكلمات\n"
                "`/on` — تفعيل المراقبة\n"
                "`/off` — إيقاف المراقبة\n"
                "`/help` — عرض هذه المساعدة\n\n"
                f"📊  **الحالة:** {'🟢 مفعّل' if monitoring['active'] else '🔴 متوقف'}\n"
                f"🔑  **الكلمات:** {len(get_keywords())}"
            )
            await event.reply(help_text)

    # ───────── مراقبة الرسائل ─────────

    @client.on(events.NewMessage(
        incoming=True,
        func=lambda e: e.is_group or e.is_channel,
    ))
    async def message_watcher(event):
        if not monitoring["active"]:
            return

        # استخراج النص
        text = event.raw_text or ""
        # دعم caption للميديا
        if not text and event.message and event.message.message:
            text = event.message.message
        if not text:
            return

        # فحص الكلمات
        keywords = get_keywords()
        if not keywords:
            return

        matched = match_keywords(text, keywords)
        if not matched:
            return

        # جمع المعلومات
        try:
            chat = await event.get_chat()
            sender = await event.get_sender()
        except Exception as e:
            log.error(f"خطأ في جلب معلومات الرسالة: {e}")
            return

        chat_title = getattr(chat, "title", "غير معروف")
        sender_name = get_sender_name(sender)
        sender_id = getattr(sender, "id", 0) if sender else 0
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg_id = event.message.id

        # بناء رابط الرسالة
        msg_link = build_message_link(chat, msg_id)

        # بناء التنبيه
        alert_lines = [
            f"👥 المجموعة: {chat_title}",
            f"👤 المرسل: {sender_name}",
            f"🆔 المعرف: ID: {sender_id}",
            f"⏰ الوقت: {now}",
            "",
            "📝 الرسالة الكاملة:",
            text,
            "",
            "🔥 للتواصل السريع انسخ هذا الرابط:",
            f"tg://user?id={sender_id}",
        ]

        if msg_link:
            alert_lines.append("")
            alert_lines.append(f"🔗 رابط الرسالة:\n{msg_link}")
        else:
            alert_lines.append("")
            alert_lines.append(f"🔍 ابحث بالمعرف: ID: {sender_id}")

        alert_lines.append("")
        alert_lines.append(f"🎯 الكلمات المتطابقة: {', '.join(matched)}")

        alert_text = "\n".join(alert_lines)

        # إرسال للـ Saved Messages
        try:
            await client.send_message("me", alert_text)
            log.info(
                f"🔔  تنبيه — [{chat_title}] من {sender_name} "
                f"(الكلمات: {', '.join(matched)})"
            )
        except errors.FloodWaitError as e:
            log.warning(f"⏳  FloodWait: انتظار {e.seconds} ثانية...")
            await asyncio.sleep(e.seconds)
            await client.send_message("me", alert_text)
        except Exception as e:
            log.error(f"❌  خطأ في إرسال التنبيه: {e}")

        # نسخ للحافظة (Termux)
        copy_to_clipboard(alert_text)

    # ───────── تشغيل ─────────

    log.info("🚀  البوت يعمل الآن... اكتب /help في Saved Messages.")
    print("=" * 50)
    print("🚀  البوت يعمل — اضغط Ctrl+C للإيقاف")
    print("📱  اكتب /help في Saved Messages للمساعدة")
    print("=" * 50)

    await client.run_until_disconnected()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("👋  تم إيقاف البوت.")
    except Exception as e:
        log.error(f"💥  خطأ غير متوقع: {e}", exc_info=True)
        sys.exit(1)
