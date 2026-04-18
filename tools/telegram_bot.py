# tools/telegram_bot.py
# Purpose: Telegram bot — receives screenshots, generates email drafts, sends on /confirm

import os
import sys
import json
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_job_info import extract_job_info
from generate_email import generate_email
from send_gmail import send_email
from download_cvs import CV_FILES, get_all_cvs

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_FILE = os.path.join(BASE_DIR, ".tmp", "state.json")

# ── State persistence ──────────────────────────────────────────────────────────

def load_state() -> dict:
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_state(state: dict):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


pending_jobs: dict = load_state()

# ── Helpers ────────────────────────────────────────────────────────────────────

def build_cv_keyboard():
    buttons = [
        InlineKeyboardButton(cv["name"], callback_data=f"cv:{cv['key']}")
        for cv in CV_FILES
    ]
    return InlineKeyboardMarkup([buttons])


def build_preview_text(job_info: dict, result: dict) -> str:
    return (
        f"📧 *To:* `{job_info['email']}`\n"
        f"📌 *Subject:* {result['subject']}\n"
        f"📄 *CV:* {result['cv_name']}\n"
        f"🏢 *Company:* {job_info.get('company') or 'N/A'}\n"
        f"💼 *Position:* {job_info.get('job_title') or 'N/A'}\n"
        f"{'─' * 30}\n\n"
        f"{result['email_body']}\n\n"
        f"{'─' * 30}\n"
        f"اكتب /confirm للإرسال | /cancel للإلغاء"
    )


def set_state(chat_id, data):
    pending_jobs[str(chat_id)] = data
    save_state(pending_jobs)


def del_state(chat_id):
    pending_jobs.pop(str(chat_id), None)
    save_state(pending_jobs)


def get_state(chat_id):
    return pending_jobs.get(str(chat_id))

# ── Handlers ───────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "مرحباً! أرسل لي صورة من أي إعلان وظيفي يحتوي على إيميل وسأجهز لك الطلب تلقائياً.\n\n"
        "بعد المراجعة اكتب /confirm للإرسال أو /cancel للإلغاء."
    )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text("جاري قراءة الصورة... ⏳")

    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    image_bytes = bytes(await file.download_as_bytearray())

    try:
        job_info = extract_job_info(image_bytes)
    except Exception as e:
        logger.error(f"extract_job_info failed: {e}")
        await update.message.reply_text(f"❌ فشل في قراءة الصورة: {e}")
        return

    if not job_info.get("email"):
        await update.message.reply_text(
            "⚠️ لم أجد إيميل في الصورة. تأكد إن الصورة تحتوي على عنوان البريد الإلكتروني."
        )
        return

    await update.message.reply_text("تم استخراج المعلومات، جاري تحليل الوظيفة... 🔍")

    try:
        result = generate_email(job_info)
    except Exception as e:
        logger.error(f"generate_email failed: {e}")
        await update.message.reply_text(f"❌ فشل في كتابة الإيميل: {e}")
        return

    if result["confidence"] == 0:
        set_state(chat_id, {"stage": "awaiting_cv_choice", "job_info": job_info})
        await update.message.reply_text(
            f"🤔 الوظيفة: *{job_info.get('job_title') or 'N/A'}*\n\n"
            f"لم أتأكد من أنسب CV. اختر أنت:",
            parse_mode="Markdown",
            reply_markup=build_cv_keyboard(),
        )
    else:
        set_state(chat_id, {"stage": "awaiting_confirm", "job_info": job_info, "result": result})
        change_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 تغيير الـ CV", callback_data="change_cv")]
        ])
        await update.message.reply_text(
            build_preview_text(job_info, result),
            parse_mode="Markdown",
            reply_markup=change_keyboard,
        )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    data = query.data

    state = get_state(chat_id)
    if not state:
        await query.message.reply_text(
            "⚠️ انتهت الجلسة أو البوت اتعيد تشغيله. أرسل الصورة مرة أخرى."
        )
        return

    if data == "change_cv":
        set_state(chat_id, {"stage": "awaiting_cv_choice", "job_info": state["job_info"]})
        await query.message.reply_text("اختر الـ CV اللي تريده:", reply_markup=build_cv_keyboard())
        return

    if data.startswith("cv:"):
        cv_key = data.split(":", 1)[1]
        job_info = state["job_info"]

        await query.message.reply_text("جاري كتابة الإيميل بناءً على الـ CV المختار... ✍️")

        try:
            result = generate_email(job_info, selected_cv_key=cv_key)
        except Exception as e:
            logger.error(f"generate_email failed: {e}")
            await query.message.reply_text(f"❌ فشل في كتابة الإيميل: {e}")
            return

        set_state(chat_id, {"stage": "awaiting_confirm", "job_info": job_info, "result": result})

        change_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 تغيير الـ CV", callback_data="change_cv")]
        ])
        await query.message.reply_text(
            build_preview_text(job_info, result),
            parse_mode="Markdown",
            reply_markup=change_keyboard,
        )


async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    state = get_state(chat_id)

    if not state or state.get("stage") != "awaiting_confirm":
        await update.message.reply_text("لا يوجد إيميل معلق للإرسال. أرسل صورة أولاً.")
        return

    job_info = state["job_info"]
    result = state["result"]

    await update.message.reply_text("جاري الإرسال... 📤")

    try:
        msg_id = send_email(
            to_email=job_info["email"],
            subject=result["subject"],
            body=result["email_body"],
            cv_path=result["cv_path"],
            html=result.get("email_html"),
        )
        del_state(chat_id)
        await update.message.reply_text(
            f"✅ تم الإرسال بنجاح!\n"
            f"📧 إلى: {job_info['email']}\n"
            f"📄 CV: {result['cv_name']}\n"
            f"🆔 ID: {msg_id}"
        )
    except Exception as e:
        logger.error(f"send_email failed: {e}")
        await update.message.reply_text(f"❌ فشل الإرسال: {e}")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if get_state(chat_id):
        del_state(chat_id)
        await update.message.reply_text("تم الإلغاء. يمكنك إرسال صورة جديدة.")
    else:
        await update.message.reply_text("لا يوجد طلب معلق حالياً.")


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN غير موجود في ملف .env")

    logger.info("Downloading CVs from Google Drive...")
    try:
        get_all_cvs()
        logger.info("CVs ready.")
    except Exception as e:
        logger.warning(f"Could not download CVs: {e}")

    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("confirm", confirm))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(handle_callback))

    logger.info("Bot is running...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
