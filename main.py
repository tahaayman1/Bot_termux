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

DEBUG_MODE = os.getenv("DEBUG_MODE", "0") == "1"
LOG_LEVEL = logging.DEBUG if DEBUG_MODE else logging.INFO

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("userbot")

# ──────────────────────────── HELPERS ───────────────────────────

def normalize_arabic(text: str) -> str:
    """إزالة التشكيل والحركات والمسافات الزائدة من النص العربي لتحسين المطابقة."""
    # إزالة الحركات العربية
    arabic_diacritics = re.compile(r"[\u064B-\u065F\u0670\u0640]")
    text = arabic_diacritics.sub("", text)
    # توحيد المسافات
    text = re.sub(r"\s+", " ", text)
    # إزالة علامات الترقيم الشائعة
    text = text.replace("؟", "").replace("!", "").replace(".", "").replace("،", "")
    return text.strip()


def match_keywords(text: str, keywords: list[dict]) -> list[str]:
    """فحص النص مقابل الكلمات بمطابقة قوية جداً."""
    matched = []
    normalized_text = normalize_arabic(text.lower())
    
    for kw in keywords:
        try:
            normalized_kw = normalize_arabic(kw["keyword"].lower())
            if kw["is_regex"]:
                if re.search(normalized_kw, normalized_text, re.IGNORECASE):
                    matched.append(kw["keyword"])
            else:
                # مطابقة قوية: التحقق من وجود كل كلمات العبارة المفتاحية
                kw_words = normalized_kw.split()
                text_words = normalized_text.split()
                
                # نفس العبارة كاملة
                if normalized_kw in normalized_text:
                    matched.append(kw["keyword"])
                # أو كل الكلمات موجودة (بأي ترتيب)
                elif all(any(word in text_word or text_word in word 
                            for text_word in text_words) 
                        for word in kw_words):
                    matched.append(kw["keyword"])
        except Exception as e:
            log.warning(f"⚠️  خطأ في فحص الكلمة {kw.get('keyword', '?')}: {e}")
    return matched


def build_message_link(chat, msg_id: int) -> str:
    """بناء رابط الرسالة."""
    if hasattr(chat, "username") and chat.username:
        return f"https://t.me/{chat.username}/{msg_id}"
    if hasattr(chat, "id"):
        # supergroup/channel خاص — internal id
        internal_id = chat.id
        return f"https://t.me/c/{internal_id}/{msg_id}"

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
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS config (
            key   TEXT PRIMARY KEY,
            value TEXT
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


def set_config(key: str, value: str):
    """تعيين إعداد في قاعدة البيانات."""
    conn = sqlite3.connect(DB_FILE)
    conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()


def get_config(key: str) -> str:
    """جلب إعداد من قاعدة البيانات."""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.execute("SELECT value FROM config WHERE key = ?", (key,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


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

def normalize_arabic(text: str) -> str:
    """إزالة التشكيل والحركات من النص العربي لتحسين المطابقة."""
    # إزالة الحركات العربية
    arabic_diacritics = re.compile(
        r"[\u064B-\u065F\u0670\u0640]"
    )
    return arabic_diacritics.sub("", text)


def match_keywords(text: str, keywords: list[dict]) -> list[str]:
    """فحص النص مقابل الكلمات. ترجع قائمة بالكلمات المتطابقة."""
    matched = []
    # تطبيع النص
    normalized_text = normalize_arabic(text.lower())
    
    for kw in keywords:
        try:
            normalized_kw = normalize_arabic(kw["keyword"].lower())
            if kw["is_regex"]:
                if re.search(normalized_kw, normalized_text, re.IGNORECASE):
                    matched.append(kw["keyword"])
            else:
                if normalized_kw in normalized_text:
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
    client.flood_sleep_threshold = 60

    await client.start()
    me = await client.get_me()
    owner_id = me.id
    
    # ═══════════ رسالة ترحيبية ═══════════
    welcome_banner = (
        "\n" + "═" * 60 + "\n"
        "🤖  **Telegram Userbot — Monitor Bot**\n\n"
        "✨  تم التطوير بواسطة: **المهندس / طه أيمن**\n"
        "📱  Developer: Eng. Taha Ayman\n\n"
        f"👤  المستخدم: {me.first_name}\n"
        f"🆔  ID: {owner_id}\n"
        f"🔑  الكلمات المفتاحية: {len(get_keywords())}\n"
        "\n" + "═" * 60 + "\n"
    )
    print(welcome_banner)
    log.info(f"✅  تم تسجيل الدخول: {me.first_name} (ID: {owner_id})")
    log.info("🚀  تم التطوير بواسطة المهندس / طه أيمن")
    
    # إرسال رسالة ترحيب للـ Saved Messages
    try:
        await client.send_message(
            "me",
            f"🤖 **البوت شغال الآن!**\n\n"
            f"✨ تم التطوير بواسطة: **المهندس / طه أيمن**\n"
            f"🔑 الكلمات المفتاحية: {len(get_keywords())}\n\n"
            f"اكتب `/help` للمساعدة"
        )
    except:
        pass

    # حالة المراقبة
    monitoring = {"active": True}

    # ───────── أوامر Saved Messages ─────────

    @client.on(events.NewMessage(
        outgoing=True,
        # from_users=owner_id,  <-- Removing this just in case, outgoing=True implies it's us
        func=lambda e: e.text and e.text.startswith("/")
    ))
    async def command_handler(event):
        text = event.raw_text.strip()
        log.info(f"⚡ DEBUG: Command detected: {text} | Chat: {event.chat_id} | Private: {event.is_private}")
                     
        if not text:
            return
        
        # تحويل لحروف صغيرة للمقارنة
        lower_text = text.lower()

        # أوامر الإدارة (إضافة/حذف) تشتغل بس في الخاص (Saved Messages)
        # ماعدا /setlog و /status ممكن يشتغل في القنوات
        if not event.is_private:
            if not (lower_text.startswith("/setlog") or lower_text.startswith("/status")):
                 return # تجاهل أي رسالة أخرى في القنوات
        
        log.debug(f"Command received: {text} in {event.chat_id}")

        # ── إضافة (+ keyword) ──
        if text.startswith("+") or lower_text.startswith("/add"):
            # استخراج الكلمات (دعم الأسطر المتعددة)
            raw_content = text[1:].strip() if text.startswith("+") else text[4:].strip()
            if not raw_content:
                 await event.reply("⚠️  الاستخدام: `+ كلمة` أو `+` ثم قائمة كلمات")
                 return
            
            lines = [l.strip() for l in raw_content.split('\n') if l.strip()]
            added = []
            exist = []
            
            for line in lines:
                is_regex = False
                kw = line
                if line.startswith("r:"):
                    is_regex = True
                    kw = line[2:].strip()
                    try:
                        re.compile(kw)
                    except:
                        continue # Skip invalid regex
                
                if add_keyword(kw, is_regex):
                    added.append(kw)
                else:
                    exist.append(kw)
            
            msg = []
            if added:
                msg.append(f"✅ **تمت الإضافة ({len(added)}):**\n" + "\n".join([f"- `{k}`" for k in added]))
            if exist:
                msg.append(f"⚠️ **موجودة مسبقاً ({len(exist)}):**\n" + "\n".join([f"- `{k}`" for k in exist]))
            
            await event.reply("\n\n".join(msg))
            log.info(f"➕ إضافات جديدة: {added}")

        # ── حذف (- keyword) ──
        elif text.startswith("-") or lower_text.startswith("/del"):
            raw_content = text[1:].strip() if text.startswith("-") else text[4:].strip()
            if not raw_content:
                 await event.reply("⚠️  الاستخدام: `- كلمة` لحذفها")
                 return

            lines = [l.strip() for l in raw_content.split('\n') if l.strip()]
            deleted = []
            not_found = []

            for line in lines:
                 if del_keyword(line):
                     deleted.append(line)
                 else:
                     not_found.append(line)
            
            msg = []
            if deleted:
                msg.append(f"🗑 **تم الحذف ({len(deleted)}):**\n" + "\n".join([f"- `{k}`" for k in deleted]))
            if not_found:
                msg.append(f"⚠️ **غير موجودة ({len(not_found)}):**\n" + "\n".join([f"- `{k}`" for k in not_found]))
            
            await event.reply("\n\n".join(msg))
            log.info(f"➖ محذوفات: {deleted}")

        # ── عرض (#) ──
        elif text == "#" or lower_text == "/list":
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
        elif lower_text == "/on":
            monitoring["active"] = True
            await event.reply("▶️  تم تفعيل المراقبة.")
            log.info("▶️  المراقبة مفعّلة.")

        # ── /off ──
        elif lower_text == "/off":
            monitoring["active"] = False
            await event.reply("⏸  تم إيقاف المراقبة.")
            log.info("⏸  المراقبة متوقفة.")

        # ── /help ──
        elif lower_text == "/help":
            help_text = (
                "📖  **أوامر البوت (Eng. Taha Ayman):**\n\n"
                "`+ كلمة` — إضافة كلمة (أو كلمات في أسطر)\n"
                "`- كلمة` — حذف كلمة (أو كلمات)\n"
                "`#` — عرض قائمة الكلمات\n"
                "`/on` — تفعيل المراقبة\n"
                "`/off` — إيقاف المراقبة\n"
                "`/status` — الحالة\n"
                "`/setlog` — تعيين القناة للتنبيهات\n\n"
                f"📊  **الحالة:** {'🟢 مفعّل' if monitoring['active'] else '🔴 متوقف'}\n"
                f"🔑  **الكلمات:** {len(get_keywords())}"
            )
            await event.reply(help_text)

        # ── /status ──
        elif lower_text == "/status":
            kw_count = len(get_keywords())
            log_channel = get_config("log_channel")
            channel_status = f"📢 قناة: `{log_channel}`" if log_channel else "📁 Saved Messages"
            
            status = "🟢 مفعّل" if monitoring["active"] else "🔴 متوقف"
            status_text = (
                f"📊 **حالة البوت:**\n\n"
                f"المراقبة: {status}\n"
                f"التنبيهات: {channel_status}\n"
                f"عدد الكلمات: {kw_count}\n\n"
                f"✨ المطور: المهندس / طه أيمن"
            )
            await event.reply(status_text)
            
        # ── /setlog (تعيين قناة للتنبيهات) ──
        elif lower_text == "/setlog":
            # يجب إرسال الأمر داخل القناة نفسها
            if event.is_private:
                await event.reply("⚠️ استخدم هذا الأمر داخل القناة التي تريد وصول التنبيهات إليها.")
                return
            
            # حفظ ID القناة
            chat_id = str(event.chat_id)
            set_config("log_channel", chat_id)
            await event.reply(f"✅ تم تعيين هذه القناة ({chat_id}) لاستلام التنبيهات!")
            log.info(f"📢 تم تحويل التنبيهات إلى القناة: {chat_id}")

        # ── /unsetlog (الرجوع للخاص) ──
        elif lower_text == "/unsetlog":
            set_config("log_channel", "")
            await event.reply("✅ رجعت التنبيهات على **Saved Messages**.")
            log.info("📁 عادت التنبيهات إلى Saved Messages.")

    # ───────── مراقبة الرسائل ─────────

    @client.on(events.NewMessage(
        incoming=True,
        func=lambda e: e.is_group or e.is_channel,
    ))
    async def message_watcher(event):
        # تسجيل كل رسالة واردة (debug)
        try:
            chat_info = await event.get_chat()
            chat_name = getattr(chat_info, "title", "Unknown")
            log.debug(f"📨 رسالة واردة من: {chat_name}")
        except:
            pass

        if not monitoring["active"]:
            log.debug("⏸ المراقبة متوقفة — تم تجاهل الرسالة")
            return

        # استخراج النص
        text = event.raw_text or ""
        # دعم caption للميديا
        if not text and event.message and event.message.message:
            text = event.message.message
        if not text:
            log.debug("⏭ رسالة بدون نص — تم التجاهل")
            return

        # فحص الكلمات
        keywords = get_keywords()
        if not keywords:
            log.warning("⚠️ لا توجد كلمات مفتاحية — لن يتم الفحص")
            return

        log.debug(f"🔍 فحص الرسالة مقابل {len(keywords)} كلمة...")
        matched = match_keywords(text, keywords)
        if not matched:
            log.debug("❌ لا يوجد تطابق")
            return

        log.info(f"✅ تطابق! الكلمات: {', '.join(matched)}")

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
            "🔴 **تنبيه جديد _(Monitor Bot)_**",
            "",
            f"📨 **الرسالة:**",
            f"> {text}",
            "",
            f"👤 **المرسل:** {sender_name}",
            f"🏷 **المجموعة:** {chat_title}",
            f"⏰ **الوقت:** {now}",
            "",
            f"🎯 `{'`, `'.join(matched)}`",
            "",
            "ــــــــــــــــــــــــــــــــــــــــــــــــ",
            "🚀 **خيارات التواصل السريع:**",
            f"1️⃣ [اضغط هنا للمراسلة (رابط 1)](tg://user?id={sender_id})",
            f"2️⃣ [اضغط هنا للمراسلة (رابط 2)](tg://openmessage?user_id={sender_id})",
        ]
        
        # إضافة رابط بروفايل لو فيه يوزرنيم
        if sender and hasattr(sender, 'username') and sender.username:
            alert_lines.append(f"3️⃣ [رابط المعرف (@{sender.username})](https://t.me/{sender.username})")
        
        if msg_link:
             alert_lines.append(f"3️⃣ [ذهاب للرسالة في الجروب]({msg_link})")

        alert_lines.append("")
        alert_lines.append("👨‍💻 تم التطوير بواسطة: **المهندس / طه أيمن**")

        alert_text = "\n".join(alert_lines)

        # إرسال للـ Saved Messages أو القناة المحددة
        target_chat = get_config("log_channel") or "me"
        try:
            # إذا كان الهدف هو قناة، تأكد من أنها رقم (int)
            if target_chat != "me":
                try:
                    target_chat = int(target_chat)
                except:
                    pass
            
            await client.send_message(target_chat, alert_text, parse_mode="md")
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

        # (تم تعطيل النسخ التلقائي بناءً على طلب المستخدم)
        # copy_to_clipboard(alert_text)

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
