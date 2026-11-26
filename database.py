# database.py
import sqlite3
import json
from datetime import datetime, timedelta

DB_PATH = "bot_mail.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                registered_at TEXT DEFAULT CURRENT_TIMESTAMP,
                is_blocked INTEGER DEFAULT 0
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                plan TEXT NOT NULL,
                started_at TEXT DEFAULT CURRENT_TIMESTAMP,
                expires_at TEXT NOT NULL,
                payment_method TEXT,
                payment_ref TEXT,
                active INTEGER DEFAULT 1
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS mailboxes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                address TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                token TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                domain TEXT,
                label TEXT DEFAULT '',
                avatar_file_id TEXT DEFAULT '',
                notifications_enabled INTEGER DEFAULT 1,
                enabled INTEGER DEFAULT 1,
                twofa_enabled INTEGER DEFAULT 0,
                twofa_code TEXT DEFAULT ''
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS admin_state (
                user_id INTEGER PRIMARY KEY,
                pending_action TEXT DEFAULT ''
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS contact_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        cur.execute("INSERT OR IGNORE INTO contact_settings (key, value) VALUES ('contact_enabled', '1')")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS contact_map (
                owner_msg_id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL
            )
        """)

        conn.commit()

        cur.execute("PRAGMA table_info(mailboxes)")
        cols = {r["name"] for r in cur.fetchall()}
        if "twofa_enabled" not in cols:
            cur.execute("ALTER TABLE mailboxes ADD COLUMN twofa_enabled INTEGER DEFAULT 0")
        if "twofa_code" not in cols:
            cur.execute("ALTER TABLE mailboxes ADD COLUMN twofa_code TEXT DEFAULT ''")
        conn.commit()


def get_user(user_id):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return cur.fetchone()


def create_or_update_user(user_id, username, first_name):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO users (user_id, username, first_name)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name
        """, (user_id, username, first_name))
        conn.commit()


def is_blocked(user_id):
    u = get_user(user_id)
    return bool(u and u["is_blocked"])


def get_all_users():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users ORDER BY registered_at DESC")
        return cur.fetchall()


def get_active_subscription(user_id):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM subscriptions
            WHERE user_id = ? AND active = 1 AND expires_at > datetime('now')
            ORDER BY expires_at DESC LIMIT 1
        """, (user_id,))
        return cur.fetchone()


def create_subscription(user_id, plan, days, payment_method, payment_ref=""):
    expires = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO subscriptions (user_id, plan, expires_at, payment_method, payment_ref)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, plan, expires, payment_method, payment_ref))
        conn.commit()


def count_user_mailboxes(user_id):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as c FROM mailboxes WHERE user_id = ?", (user_id,))
        return cur.fetchone()["c"]


def can_create_mailbox(user_id):
    from config import FREE_EMAIL_LIMIT
    if get_active_subscription(user_id):
        return True, ""
    if count_user_mailboxes(user_id) >= FREE_EMAIL_LIMIT:
        return False, f"لقد استنفدت حصتك المجانية ({FREE_EMAIL_LIMIT}). اشترك للمتابعة."
    return True, ""


def add_mailbox(user_id, address, password, token, domain, label=""):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO mailboxes (user_id, address, password, token, domain, label)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, address, password, token, domain, label))
        conn.commit()


def get_user_mailboxes(user_id):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM mailboxes WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
        return cur.fetchall()


def get_mailbox_by_address(user_id, address):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM mailboxes WHERE user_id = ? AND address = ?", (user_id, address))
        return cur.fetchone()


def update_mailbox_field(user_id, address, field, value):
    allowed = {"password", "token", "label", "avatar_file_id", "notifications_enabled", "enabled",
               "twofa_enabled", "twofa_code"}
    if field not in allowed:
        return False
    with get_conn() as conn:
        conn.execute(f"UPDATE mailboxes SET {field} = ? WHERE user_id = ? AND address = ?",
                     (value, user_id, address))
        conn.commit()
    return True


def delete_mailbox(user_id, address):
    with get_conn() as conn:
        conn.execute("DELETE FROM mailboxes WHERE user_id = ? AND address = ?", (user_id, address))
        conn.commit()


def delete_all_mailboxes(user_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM mailboxes WHERE user_id = ?", (user_id,))
        conn.commit()


def set_twofa(user_id, address, enabled, code=""):
    with get_conn() as conn:
        conn.execute(
            "UPDATE mailboxes SET twofa_enabled = ?, twofa_code = ? WHERE user_id = ? AND address = ?",
            (1 if enabled else 0, code, user_id, address)
        )
        conn.commit()


def verify_twofa(user_id, address, code):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT twofa_code FROM mailboxes WHERE user_id = ? AND address = ?",
            (user_id, address)
        )
        row = cur.fetchone()
        return bool(row and row["twofa_code"] and row["twofa_code"] == code.strip())


def set_admin_pending(user_id, action):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO admin_state (user_id, pending_action) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET pending_action = excluded.pending_action
        """, (user_id, action))
        conn.commit()


def get_admin_pending(user_id):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT pending_action FROM admin_state WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        return row["pending_action"] if row else ""


def clear_admin_pending(user_id):
    set_admin_pending(user_id, "")


def get_contact_enabled():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM contact_settings WHERE key = 'contact_enabled'")
        row = cur.fetchone()
        return bool(row and row["value"] == "1")


def set_contact_enabled(enabled: bool):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO contact_settings (key, value) VALUES ('contact_enabled', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            ("1" if enabled else "0",)
        )
        conn.commit()


def save_contact_map(owner_msg_id, user_id):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO contact_map (owner_msg_id, user_id) VALUES (?, ?)",
            (owner_msg_id, user_id)
        )
        conn.commit()


def get_contact_user(owner_msg_id):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM contact_map WHERE owner_msg_id = ?", (owner_msg_id,))
        row = cur.fetchone()
        return row["user_id"] if row else None


def export_users_txt():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users ORDER BY user_id")
        rows = cur.fetchall()
    return "\n".join(f"{r['user_id']}|{r['username'] or ''}|{r['first_name'] or ''}|{r['registered_at']}" for r in rows)


def import_users_txt(content):
    count = 0
    with get_conn() as conn:
        for line in content.strip().splitlines():
            parts = line.split("|")
            if not parts or not parts[0].strip():
                continue
            try:
                uid = int(parts[0])
                uname = parts[1] if len(parts) > 1 else ""
                fname = parts[2] if len(parts) > 2 else ""
                reg = parts[3] if len(parts) > 3 else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                conn.execute("""
                    INSERT OR IGNORE INTO users (user_id, username, first_name, registered_at)
                    VALUES (?, ?, ?, ?)
                """, (uid, uname, fname, reg))
                count += 1
            except ValueError:
                continue
        conn.commit()
    return count


def export_emails_json(user_id=None):
    with get_conn() as conn:
        cur = conn.cursor()
        if user_id is not None:
            cur.execute("SELECT * FROM mailboxes WHERE user_id = ?", (user_id,))
        else:
            cur.execute("SELECT * FROM mailboxes")
        rows = cur.fetchall()

    data = []
    for r in rows:
        data.append({
            "user_id": r["user_id"],
            "address": r["address"],
            "password": r["password"],
            "token": r["token"],
            "created_at": r["created_at"],
            "domain": r["domain"],
            "label": r["label"],
            "avatar_file_id": r["avatar_file_id"],
            "notifications_enabled": r["notifications_enabled"],
            "enabled": r["enabled"],
            "twofa_enabled": r["twofa_enabled"],
            "twofa_code": r["twofa_code"],
        })
    return json.dumps(data, ensure_ascii=False, indent=2)


def import_emails_json(content):
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return 0
    count = 0
    with get_conn() as conn:
        for item in data:
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO mailboxes
                    (user_id, address, password, token, domain, label, avatar_file_id, notifications_enabled, enabled, twofa_enabled, twofa_code)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item["user_id"], item["address"], item["password"],
                    item.get("token", ""), item.get("domain", ""), item.get("label", ""),
                    item.get("avatar_file_id", ""), item.get("notifications_enabled", 1),
                    item.get("enabled", 1), item.get("twofa_enabled", 0), item.get("twofa_code", "")
                ))
                count += 1
            except Exception:
                continue
        conn.commit()
    return count


def get_stats():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as c FROM users")
        users = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(*) as c FROM mailboxes")
        mails = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(*) as c FROM subscriptions WHERE active = 1 AND expires_at > datetime('now')")
        subs = cur.fetchone()["c"]
    return {"users": users, "mailboxes": mails, "active_subs": subs}