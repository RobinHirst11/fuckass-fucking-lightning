import asyncio
import json
import sqlite3
import threading
import time
import websockets
from datetime import datetime, timezone
from flask import Flask, jsonify, render_template
from flask_socketio import SocketIO

# --- Configs ---
ws_site = "wss://ws2.blitzortung.org/"
db_file = "lightning_strikes.db"
handshake_message = json.dumps({"a": 111})
interval_thingy = 0.1  # how often we send data to the browser

app = Flask(__name__)
socketio = SocketIO(app, async_mode="threading")

# global buffer for strikes
strike_buffer = []
buffer_lock = threading.Lock()


def init_db():
    print(f"Setting up database at '{db_file}'...")
    con = sqlite3.connect(db_file, check_same_thread=False)
    cur = con.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS strikes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            strike_time_ns INTEGER NOT NULL,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            delay REAL,
            mds INTEGER,
            status INTEGER,
            received_at TEXT NOT NULL,
            UNIQUE (strike_time_ns, lat, lon)
        )
    """
    )
    con.commit()
    con.close()
    print("Database setup complete.")


def decode_data(b):
    e = {}
    d = list(b)
    c = f = g = d[0]
    result = [c]
    h = o = 256
    for i in range(1, len(d)):
        a = ord(d[i])
        a = d[i] if a < h else e.get(a, f + c)
        result.append(a)
        c = a[0]
        e[o] = f + c
        o += 1
        f = a
    return "".join(result)


async def get_data_from_blitz():
    db_connection = sqlite3.connect(db_file, check_same_thread=False)
    while True:
        try:
            async with websockets.connect(ws_site) as ws:
                print(f"WebSocket connected to {ws_site}")
                await ws.send(handshake_message)
                print("Handshake sent. Listening...")
                async for raw_message in ws:
                    try:
                        strike_data = json.loads(decode_data(raw_message))
                        if "lat" in strike_data and "lon" in strike_data:
                            with buffer_lock:
                                strike_buffer.append(
                                    {
                                        "lat": strike_data.get("lat"),
                                        "lon": strike_data.get("lon"),
                                    }
                                )
                            # this was too slow, sending one by one. batching is better
                            # data_for_browser = {
                            #     "lat": strike_data.get("lat"),
                            #     "lon": strike_data.get("lon"),
                            # }
                            # socketio.emit("new_strike", data_for_browser)
                            # also writing to db here was maybe a bad spot
                            cur = db_connection.cursor()
                            cur.execute(
                                "INSERT OR IGNORE INTO strikes (strike_time_ns, lat, lon, received_at) VALUES (?, ?, ?, ?)",
                                (
                                    strike_data.get("time"),
                                    strike_data.get("lat"),
                                    strike_data.get("lon"),
                                    datetime.now(timezone.utc).isoformat(),
                                ),
                            )
                            db_connection.commit()
                    except Exception:
                        pass
        except Exception as e:
            print(f"Connection error: {e}. Retrying in 5s...")
            await asyncio.sleep(5)


def sender_func():
    """sends the buffer to the browser every so often"""
    global strike_buffer
    while True:
        time.sleep(interval_thingy)
        if strike_buffer:
            with buffer_lock:
                batch_of_dots = strike_buffer[:]
                strike_buffer.clear()
            if batch_of_dots:
                socketio.emit("strike_batch", batch_of_dots)


@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    init_db()

    print("Starting listener thread...")
    listener_thread = threading.Thread(
        target=lambda: asyncio.run(get_data_from_blitz()), daemon=True
    )
    listener_thread.start()

    print("Starting sender thread...")
    sender_thread = threading.Thread(target=sender_func, daemon=True)
    sender_thread.start()

    print("Starting Flask server...")
    socketio.run(app, host="0.0.0.0", port=5000, debug=False)
