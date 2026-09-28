"""ساخت یک فایل اکسل نمونه برای تست ربات."""
import sys
import io

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import pandas as pd

df = pd.DataFrame(
    {
        "نام": ["علی رضایی", "سارا محمدی", "امیر حسینی"],
        "تاریخ تولد": ["1370/05/12", "1368/11/02", "1375/01/20"],
    }
)
df.to_excel("birthdays.xlsx", index=False)
print("فایل birthdays.xlsx ساخته شد.")
