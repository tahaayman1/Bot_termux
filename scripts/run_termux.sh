#!/bin/bash
# ─────────────────────────────────────────
#  Telegram Userbot — سكربت التشغيل لـ Termux
# ─────────────────────────────────────────

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$SCRIPT_DIR"

# تحقق من وجود .env
if [ ! -f ".env" ]; then
    echo "❌  ملف .env غير موجود!"
    echo "   انسخ .env.example إلى .env وعدّل القيم:"
    echo "   cp .env.example .env"
    echo "   nano .env"
    exit 1
fi

# تفعيل Virtual Environment إن وجد
if [ -d "venv" ]; then
    echo "📦  تفعيل Virtual Environment..."
    source venv/bin/activate
fi

# تحقق من المتطلبات
echo "🔍  التحقق من المتطلبات..."
pip install -q -r requirements.txt 2>/dev/null

# منع Termux من النوم
if command -v termux-wake-lock &>/dev/null; then
    echo "🔒  تفعيل Wake Lock..."
    termux-wake-lock
fi

# تشغيل البوت
echo "🚀  جاري تشغيل البوت..."
python main.py
