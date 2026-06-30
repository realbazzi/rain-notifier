import os
import time
import requests
import mysql.connector

API_URL = os.getenv("API_URL")
BOT_TOKEN = os.getenv("BOT_TOKEN")

db = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASS"),
    database=os.getenv("DB_NAME"),
    autocommit=True
)

cursor = db.cursor(dictionary=True)


# ---------------- TELEGRAM ----------------

def tg_send(chat_id, text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10
        )
    except:
        pass


def get_updates(offset=None):
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates",
            params={"timeout": 10, "offset": offset},
            timeout=15
        )
        return r.json()
    except:
        return {"result": []}


# ---------------- DB ----------------

def add_user(chat_id):
    cursor.execute(
        "INSERT IGNORE INTO users (chat_id) VALUES (%s)",
        (chat_id,)
    )


def get_users():
    cursor.execute("SELECT chat_id FROM users")
    return cursor.fetchall()


def save_rain(rain, status):
    if not rain:
        return

    cursor.execute("""
        INSERT INTO rains (rain_id, points, durationSec, startedAt, expiresAt, totalClaims, status)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
    """, (
        rain.get("id"),
        rain.get("points"),
        rain.get("durationSec"),
        rain.get("startedAt"),
        rain.get("expiresAt"),
        rain.get("totalClaims", 0),
        status
    ))


def get_stats():
    cursor.execute("SELECT COUNT(*) as c FROM rains")
    total = cursor.fetchone()["c"]

    cursor.execute("SELECT COALESCE(SUM(points),0) as p FROM rains")
    points = cursor.fetchone()["p"]

    return total, points


def get_last_rain():
    cursor.execute("SELECT * FROM rains ORDER BY id DESC LIMIT 1")
    return cursor.fetchone()


# ---------------- API ----------------

def fetch_rain():
    try:
        r = requests.get(API_URL, timeout=10).json()

        # WICHTIG: API liefert {"rain": null}
        if not r or r.get("rain") is None:
            return None

        return r["rain"]

    except:
        return None


# ---------------- FORMAT ----------------

def format_start(r):
    return (
        f"🟢 RAIN GESTARTET\n\n"
        f"ID: {r['id']}\n"
        f"Punkte: {r['points']}\n"
        f"Dauer: {r['durationSec']}s"
    )


def format_end(r):
    return (
        f"🔴 RAIN BEENDET\n\n"
        f"ID: {r['id']}\n"
        f"Punkte: {r['points']}\n"
        f"Dauer: {r['durationSec']}s"
    )


# ---------------- BOT LOOP ----------------

def run():
    last_rain = None
    offset = None

    while True:

        # -------- Telegram commands --------
        updates = get_updates(offset)

        for u in updates.get("result", []):
            offset = u["update_id"] + 1

            msg = u.get("message", {})
            chat_id = msg.get("chat", {}).get("id")
            text = msg.get("text", "")

            if not chat_id:
                continue

            add_user(chat_id)

            if text == "/start":
                tg_send(chat_id, "🤖 Bot läuft. Rains werden automatisch überwacht.")

            elif text == "/stats":
                total, points = get_stats()
                tg_send(chat_id, f"📊 Stats:\nRains: {total}\nPunkte: {points}")

            elif text == "/lastrain":
                last = get_last_rain()
                if last:
                    tg_send(chat_id,
                        f"📌 Letzter Rain\n\n"
                        f"ID: {last['rain_id']}\n"
                        f"Punkte: {last['points']}"
                    )
                else:
                    tg_send(chat_id, "Keine Daten")

        # -------- API check --------
        rain = fetch_rain()
        users = get_users()

        active = rain is not None
        was_active = last_rain is not None

        # 🟢 START
        if active and not was_active:
            for u in users:
                tg_send(u["chat_id"], format_start(rain))

#--            save_rain(rain, "started")
            last_rain = rain

        # 🔴 END
        elif not active and was_active:
            for u in users:
                tg_send(u["chat_id"], format_end(last_rain))

            save_rain(last_rain, "ended")
            last_rain = None

        time.sleep(5)


if __name__ == "__main__":
    run()
