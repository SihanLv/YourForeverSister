import os
import sqlite3
import datetime

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.getcwd(), "data", "data.db"))
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
_conn.execute("PRAGMA foreign_keys = ON")


def init_db():
    _conn.execute(
        "CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, frequency INTEGER NOT NULL, salutation INTEGER NOT NULL, birth_year INTEGER, birth_month INTEGER, birth_day INTEGER)"
    )
    _conn.commit()
    cur = _conn.execute("PRAGMA table_info(users)")
    cols = {row[1] for row in cur.fetchall()}
    for col in ["birth_year", "birth_month", "birth_day"]:
        if col not in cols:
            _conn.execute(f"ALTER TABLE users ADD COLUMN {col} INTEGER")
    _conn.commit()


def _freq_to_int(f: str | int) -> int:
    if isinstance(f, int):
        return f
    return {"monthly": 0, "weekly": 1, "holiday": 2}.get(f, 0)


def _sal_to_int(s: str | int) -> int:
    if isinstance(s, int):
        return s
    return {"哥哥": 0, "姐姐": 1}.get(s, 1)


def _parse_birthday(b: str | None):
    if not b:
        return None
    try:
        y, m, d = b.split("/")
        return int(y), int(m), int(d)
    except Exception:
        return None


def add_user(
    email: str, frequency: str | int, salutation: str | int, birthday: str | None
):
    fy = _freq_to_int(frequency)
    sl = _sal_to_int(salutation)
    b = _parse_birthday(birthday)
    if b:
        _conn.execute(
            "INSERT INTO users (email, frequency, salutation, birth_year, birth_month, birth_day) VALUES (?, ?, ?, ?, ?, ?)",
            (email, fy, sl, b[0], b[1], b[2]),
        )
    else:
        _conn.execute(
            "INSERT INTO users (email, frequency, salutation) VALUES (?, ?, ?)",
            (email, fy, sl),
        )
    _conn.commit()


def get_user(email: str):
    cur = _conn.execute(
        "SELECT email, frequency, salutation, birth_year, birth_month, birth_day FROM users WHERE email=?",
        (email,),
    )
    row = cur.fetchone()
    if not row:
        return None
    by = row[3]
    bm = row[4]
    bd = row[5]
    bstr = None
    if by and bm and bd:
        bstr = f"{by}/{bm}/{bd}"
    return {
        "email": row[0],
        "frequency": row[1],
        "salutation": row[2],
        "birth_year": by,
        "birth_month": bm,
        "birth_day": bd,
        "birthday": bstr,
    }


def update_user(
    email: str, frequency: str | int, salutation: str | int, birthday: str | None
):
    fy = _freq_to_int(frequency)
    sl = _sal_to_int(salutation)
    b = _parse_birthday(birthday)
    if b:
        _conn.execute(
            "UPDATE users SET frequency=?, salutation=?, birth_year=?, birth_month=?, birth_day=? WHERE email=?",
            (fy, sl, b[0], b[1], b[2], email),
        )
    else:
        _conn.execute(
            "UPDATE users SET frequency=?, salutation=? WHERE email=?",
            (fy, sl, email),
        )
    _conn.commit()


def remove_user(email: str):
    _conn.execute("DELETE FROM users WHERE email=?", (email,))
    _conn.commit()


def _freq_to_str(f: int) -> str:
    return {0: "monthly", 1: "weekly", 2: "holiday"}.get(
        int(f) if f is not None else 0, "monthly"
    )


def _sal_to_str(s: int) -> str:
    return {0: "哥哥", 1: "姐姐"}.get(int(s) if s is not None else 1, "姐姐")


def list_users():
    cur = _conn.execute(
        "SELECT email, frequency, salutation, birth_year, birth_month, birth_day FROM users"
    )
    rows = cur.fetchall()
    res = []
    for r in rows:
        by, bm, bd = r[3], r[4], r[5]
        bstr = f"{by}/{bm}/{bd}" if by and bm and bd else None
        res.append(
            {
                "email": r[0],
                "frequency": _freq_to_str(r[1]),
                "salutation": _sal_to_str(r[2]),
                "birth_year": by,
                "birth_month": bm,
                "birth_day": bd,
                "birthday": bstr,
            }
        )
    return res


def list_birthday_today_group():
    d = datetime.date.today()
    cur = _conn.execute(
        "SELECT birth_year, email, frequency, salutation FROM users WHERE birth_month=? AND birth_day=? ORDER BY birth_year",
        (d.month, d.day),
    )
    rows = cur.fetchall()
    groups: dict[str, list[dict]] = {}
    for by, email, freq, sal in rows:
        key = str(by) if by else "unknown"
        groups.setdefault(key, []).append(
            {
                "email": email,
                "frequency": _freq_to_str(freq),
                "salutation": _sal_to_str(sal),
                "birth_year": by,
            }
        )
    return groups
