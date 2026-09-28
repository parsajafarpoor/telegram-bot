"""خواندن فایل اکسل تولدها و تبدیل تاریخ‌ها به تقویم شمسی."""
import datetime
import logging

import jdatetime
import pandas as pd

log = logging.getLogger(__name__)

NAME_COLUMNS = ["نام", "name", "Name", "نام و نام خانوادگی"]
DATE_COLUMNS = ["تاریخ تولد", "birthday", "Birthday", "تولد", "date", "Date"]


def _pick_column(columns, candidates):
    for c in candidates:
        if c in columns:
            return c
    return None


def _to_jalali_month_day(value):
    """یک مقدار سلول اکسل (رشته یا تاریخ) را به (ماه, روز) شمسی تبدیل می‌کند."""
    if pd.isna(value):
        return None

    # سلول اکسل که به صورت تاریخ واقعی ذخیره شده (میلادی فرض می‌شود)
    if isinstance(value, (datetime.datetime, datetime.date, pd.Timestamp)):
        g = value.date() if isinstance(value, datetime.datetime) else value
        if isinstance(g, pd.Timestamp):
            g = g.date()
        j = jdatetime.date.fromgregorian(date=g)
        return j.month, j.day

    text = str(value).strip()
    if not text:
        return None

    # جدا کردن با / یا - یا فاصله
    parts = None
    for sep in ("/", "-"):
        if sep in text:
            parts = text.split(sep)
            break
    if parts is None:
        parts = text.split()

    if len(parts) < 2:
        log.warning("تاریخ قابل شناسایی نیست: %r", value)
        return None

    try:
        nums = [int(p) for p in parts]
    except ValueError:
        log.warning("تاریخ قابل تبدیل به عدد نیست: %r", value)
        return None

    # فرمت‌های محتمل: YYYY/MM/DD یا DD/MM/YYYY یا MM/DD
    if len(nums) == 3:
        if nums[0] > 1000:
            year, month, day = nums
        else:
            day, month, year = nums
        if year > 1500:
            # سال میلادی است
            g = datetime.date(year, month, day)
            j = jdatetime.date.fromgregorian(date=g)
            return j.month, j.day
        # سال شمسی است
        return month, day

    if len(nums) == 2:
        month, day = nums
        return month, day

    return None


def load_birthdays(path: str):
    """فایل اکسل را می‌خواند و لیستی از {name, month, day} برمی‌گرداند."""
    df = pd.read_excel(path)
    df.columns = [str(c).strip() for c in df.columns]

    name_col = _pick_column(df.columns, NAME_COLUMNS)
    date_col = _pick_column(df.columns, DATE_COLUMNS)

    if name_col is None or date_col is None:
        raise ValueError(
            "ستون نام یا تاریخ تولد در فایل اکسل پیدا نشد. "
            f"ستون‌های موجود: {list(df.columns)}. "
            "لطفاً یکی از این نام‌ها را برای ستون‌ها استفاده کنید: "
            f"نام -> {NAME_COLUMNS} / تاریخ -> {DATE_COLUMNS}"
        )

    people = []
    for _, row in df.iterrows():
        name = row[name_col]
        if pd.isna(name):
            continue
        md = _to_jalali_month_day(row[date_col])
        if md is None:
            continue
        month, day = md
        people.append({"name": str(name).strip(), "month": month, "day": day})

    return people


def upcoming(people, days_ahead: int = 30, today: jdatetime.date = None):
    """افرادی که تولدشان در N روز آینده است را به ترتیب فاصله برمی‌گرداند."""
    if today is None:
        today = jdatetime.date.today()

    result = []
    for p in people:
        for offset in range(days_ahead + 1):
            d = today + datetime.timedelta(days=offset)
            if d.month == p["month"] and d.day == p["day"]:
                result.append({**p, "days_left": offset, "date": d})
                break
    result.sort(key=lambda x: x["days_left"])
    return result


def people_with_birthday_in(people, target_date: jdatetime.date):
    return [p for p in people if p["month"] == target_date.month and p["day"] == target_date.day]


def people_due_within(people, days_before: int, today: jdatetime.date = None):
    """افرادی که تولدشان بین ۱ تا days_before روز آینده است را برمی‌گرداند
    (به همراه فاصله‌ی واقعی و تاریخ دقیق تولد در همین سال شمسی)."""
    if today is None:
        today = jdatetime.date.today()

    result = []
    for p in people:
        for offset in range(1, days_before + 1):
            d = today + datetime.timedelta(days=offset)
            if d.month == p["month"] and d.day == p["day"]:
                result.append({**p, "days_left": offset, "date": d})
                break
    return result
