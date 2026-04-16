import os

print("ENV KEYS:", list(os.environ.keys()))
print("TOKEN RAW:", os.environ.get("TELEGRAM_TOKEN"))
