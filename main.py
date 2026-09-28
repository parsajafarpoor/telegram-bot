"""
ربات تلگرام یادآوری تولد
نام‌ها و تاریخ تولدها را از یک فایل اکسل می‌خواند و ۵ روز قبل از تولد هر نفر
یک پیام یادآوری (با تاریخ شمسی) در کانال/گروه تنظیم‌شده ارسال می‌کند.
"""
import datetime
import io
import logging
import os
import sys
from zoneinfo import ZoneInfo

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

import jdatetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from birthdays import load_birthdays, upcoming, people_due_within
from notified_store import already_notified, mark_notified

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
EXCEL_PATH = os.getenv("EXCEL_PATH", "birthdays.xlsx")
DAYS_BEFORE = int(os.getenv("DAYS_BEFORE", "5"))
NOTIFY_TIME = os.getenv("NOTIFY_TIME", "09:00")
TEHRAN = ZoneInfo("Asia/Tehran")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
log = logging.getLogger(__name__)

WEEKDAYS_FA = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنج‌شنبه", "جمعه", "شنبه", "یکشنبه"]
MONTHS_FA = [
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
]


def format_jalali(d: jdatetime.date) -> str:
    return f"{d.day} {MONTHS_FA[d.month - 1]} {d.year}"


def get_people():
    return load_birthdays(EXCEL_PATH)


async def daily_check(context: ContextTypes.DEFAULT_TYPE):
    try:
        people = get_people()
    except Exception as e:
        log.exception("خطا در خواندن فایل اکسل: %s", e)
        return

    today = jdatetime.date.today()
    due = people_due_within(people, DAYS_BEFORE, today=today)
    due = [p for p in due if not already_notified(p, today.year)]

    if not due:
        log.info("کسی با یادآوری معلق (بین ۱ تا %s روز تا تولد) پیدا نشد.", DAYS_BEFORE)
        return

    if not CHAT_ID:
        log.warning("CHAT_ID تنظیم نشده؛ پیام ارسال نمی‌شود.")
        return

    for p in due:
        text = (
            f"🎂 یادآوری تولد!\n\n"
            f"{p['days_left']} روز دیگر، تولد «{p['name']}» است.\n"
            f"📅 تاریخ: {format_jalali(p['date'])}"
        )
        await context.bot.send_message(chat_id=CHAT_ID, text=text)
        mark_notified(p, today.year)
        log.info("پیام یادآوری برای %s ارسال شد (%s روز مانده).", p["name"], p["days_left"])


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام! من ربات یادآوری تولد هستم.\n"
        f"هر روز ساعت {NOTIFY_TIME} به وقت تهران بررسی می‌کنم و "
        f"{DAYS_BEFORE} روز قبل از تولد هر نفر یادآوری می‌فرستم.\n\n"
        "دستورها:\n"
        "/chatid - نمایش آیدی همین چت\n"
        "/list - نمایش تولدهای ۳۰ روز آینده\n"
        "/check - اجرای فوری بررسی و ارسال یادآوری (تست)\n"
        "/reload - خواندن دوباره فایل اکسل"
    )


async def cmd_chatid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    await update.message.reply_text(f"آیدی این چت: `{chat.id}`", parse_mode="Markdown")


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        people = get_people()
    except Exception as e:
        await update.message.reply_text(f"خطا در خواندن فایل اکسل:\n{e}")
        return

    items = upcoming(people, days_ahead=30)
    if not items:
        await update.message.reply_text("در ۳۰ روز آینده تولدی ثبت نشده.")
        return

    lines = ["📋 تولدهای ۳۰ روز آینده:\n"]
    for it in items:
        lines.append(f"• {it['name']} — {it['days_left']} روز دیگر ({format_jalali(it['date'])})")
    await update.message.reply_text("\n".join(lines))


async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("در حال بررسی...")
    await daily_check(context)
    await update.message.reply_text("بررسی انجام شد (در صورت وجود مورد، پیام به CHAT_ID ارسال شد).")


async def cmd_reload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        people = get_people()
    except Exception as e:
        await update.message.reply_text(f"خطا در خواندن فایل اکسل:\n{e}")
        return
    await update.message.reply_text(f"فایل اکسل با موفقیت خوانده شد. تعداد افراد: {len(people)}")


def main():
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN در فایل .env تنظیم نشده است.")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("chatid", cmd_chatid))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("check", cmd_check))
    app.add_handler(CommandHandler("reload", cmd_reload))

    hour, minute = (int(x) for x in NOTIFY_TIME.split(":"))
    app.job_queue.run_daily(
        daily_check, time=datetime.time(hour=hour, minute=minute, tzinfo=TEHRAN)
    )
    # بررسی فوری هنگام روشن/بالا آمدن ربات، برای جبران روزهایی که سیستم خاموش بوده
    app.job_queue.run_once(daily_check, when=5)

    log.info("ربات در حال اجراست... (ارسال روزانه ساعت %s به وقت تهران)", NOTIFY_TIME)
    app.run_polling()


if __name__ == "__main__":
    main()
