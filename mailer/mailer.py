import os
import json
import time
import datetime
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.utils import formataddr
from email import encoders
from openai import OpenAI
from backend.db import list_users, list_birthday_today_group
from lunar_python import Solar
from . import prompt as prompt


def _today():
    return datetime.datetime.today()


def _date_str(d):
    return d.strftime("%Y-%m-%d")


def _ymd_cn(d):
    return f"{d.year}年{d.month}月{d.day}日"


def _ensure_dir(p):
    if not os.path.isdir(p):
        os.makedirs(p, exist_ok=True)


def _calendar_client():
    url = os.environ.get("CALENDAR_API_URL", "")
    key = os.environ.get("CALENDAR_API_KEY", "")
    return url, key


def get_today_holiday():
    d = _today()
    s = Solar.fromYmd(d.year, d.month, d.day)
    lunar = s.getLunar()
    names = []
    try:
        names += lunar.getFestivals()
        names += lunar.getOtherFestivals()
    except Exception:
        names = []
    try:
        jq = lunar.getJieQi()
        if jq:
            names.append(jq)
    except Exception:
        pass
    if names:
        return {"name": names[0]}
    url, key = _calendar_client()
    if not url or not key:
        path = os.path.join(os.getcwd(), "data", "festivals.csv")
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split(",")
                    if len(parts) >= 2 and parts[0] == _date_str(d)[5:]:
                        return {"name": parts[1]}
        return None
    try:
        r = requests.get(url, params={"date": _date_str(d), "key": key}, timeout=15)
        if r.status_code != 200:
            return None
        j = r.json()
        for k in ["holiday", "festival", "data", "events", "holidays"]:
            v = j.get(k)
            if isinstance(v, list) and len(v) > 0:
                x = v[0]
                name = x.get("name") or x.get("title") or x.get("festival")
                if name:
                    return {"name": name}
        name = j.get("name") or j.get("title")
        if name:
            return {"name": name}
    except Exception:
        return None
    return None


def get_upcoming_events(days=7):
    res = []
    for i in range(days):
        d = _today() + datetime.timedelta(days=i)
        s = Solar.fromYmd(d.year, d.month, d.day)
        lunar = s.getLunar()
        names = []
        try:
            jq = lunar.getJieQi()
            if jq:
                names.append(jq)
        except Exception:
            pass
        try:
            names += lunar.getFestivals()
        except Exception:
            pass
        if names:
            res.append({"date": _date_str(d), "name": names[0]})
    if res:
        return res
    url, key = _calendar_client()
    if not url or not key:
        path = os.path.join(os.getcwd(), "data", "festivals.csv")
        if os.path.isfile(path):
            out = []
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split(",")
                    if len(parts) >= 2:
                        out.append({"date": parts[0], "name": parts[1]})
            upcoming = set(
                _date_str(_today() + datetime.timedelta(days=i))[5:]
                for i in range(1, days + 1)
            )
            return [x for x in out if x["date"] in upcoming]
        return []
    try:
        for i in range(1, days + 1):
            d = _today() + datetime.timedelta(days=i)
            r = requests.get(url, params={"date": _date_str(d), "key": key}, timeout=15)
            if r.status_code != 200:
                continue
            j = r.json()
            name = None
            for k in ["holiday", "festival", "data", "events", "holidays"]:
                v = j.get(k)
                if isinstance(v, list) and len(v) > 0:
                    x = v[0]
                    name = x.get("name") or x.get("title") or x.get("festival")
                    break
            if not name:
                name = j.get("name") or j.get("title")
            if name:
                res.append({"date": _date_str(d), "name": name})
    except Exception:
        pass
    return res


def _client():
    key = os.environ.get("MODEL_KEY", "")
    url = os.environ.get("MODEL_URL", "")
    return OpenAI(api_key=key, base_url=url)


def _model_name():
    return os.environ.get("MODEL_NAME", "deepseek-ai/DeepSeek-V3")


def _img_model_name():
    return os.environ.get("IMG_MODEL_NAME", "Kwai-Kolors/Kolors")


def _json_prompt_for_image(text: str):
    client = _client()
    j = (
        client.chat.completions.create(
            model=_model_name(),
            messages=prompt.img_prompt_messages(text),
            max_tokens=4096,
            temperature=0.7,
            stream=False,
            response_format={"type": "json_object"},
        )
        .choices[0]
        .message.content
    )
    return json.loads(j)


_last_generate_image_time = 0


def _generate_image(prompt: str, negative_prompt: str, size: str):
    global _last_generate_image_time
    if time.time() - _last_generate_image_time < 35:
        time.sleep(max(0, 35 - (time.time() - _last_generate_image_time)))
    url = os.environ.get("MODEL_URL", "").rstrip("/") + "/images/generations"
    key = os.environ.get("MODEL_KEY", "")
    r = requests.post(
        url,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": _img_model_name(),
            "prompt": prompt,
            "size": size,
            "negative_prompt": negative_prompt,
        },
        timeout=60,
    )
    j = r.json()
    data = j.get("data") or []
    if not data:
        raise RuntimeError("image generation failed")
    img_url = data[0].get("url")
    if not img_url:
        raise RuntimeError("image url missing")
    img = requests.get(img_url, timeout=60).content
    _last_generate_image_time = time.time()
    return img


def _compose_mail(subject: str, text: str, img: bytes, to_name: str, to_email: str):
    msg = MIMEMultipart("related")
    msg["From"] = formataddr(["YourForeverSister", os.environ.get("SMTP_EMAIL", "")])
    msg["To"] = formataddr([to_name, to_email])
    msg["Subject"] = subject
    alt = MIMEMultipart("alternative")
    msg.attach(alt)
    alt.attach(MIMEText(text, "plain", "utf-8"))
    html = f'<html><body><p style="white-space: pre-wrap;">{text}</p><img src="cid:img" style="max-width:100%;"></body></html>'
    alt.attach(MIMEText(html, "html", "utf-8"))
    mime = MIMEBase("image", "png")
    mime.set_payload(img)
    encoders.encode_base64(mime)
    mime.add_header("Content-ID", "<img>")
    msg.attach(mime)
    return msg


def _send_bcc(subject: str, text: str, img: bytes, recipients: list[str]):
    sender = os.environ.get("SMTP_EMAIL", "")
    password = os.environ.get("SMTP_KEY", "")
    server = smtplib.SMTP_SSL(
        os.environ.get("SMTP_SERVER", ""), int(os.environ.get("SMTP_PORT", 465))
    )
    server.login(sender, password)
    to_addr = recipients[0] if recipients else sender
    msg = _compose_mail(subject, text, img, "You", to_addr)
    server.sendmail(sender, recipients, msg.as_string())
    server.quit()


def generate_today_cache():
    users = list_users()
    today = _today()
    is_month_start = today.day == 1
    is_monday = today.weekday() == 0
    holiday = get_today_holiday()
    upcoming = get_upcoming_events(7)
    bday_groups = list_birthday_today_group()
    bday_today = set()
    for _, recs in bday_groups.items():
        for r in recs:
            bday_today.add(r["email"])
    targets = []
    if is_month_start:
        targets += [u for u in users if u["frequency"] == "monthly"]
    if is_monday:
        targets += [u for u in users if u["frequency"] == "weekly"]
    if holiday:
        targets += [u for u in users if u["frequency"] == "holiday"]
    targets = [u for u in targets if u["email"] not in bday_today]
    groups_general = {"哥哥": [], "姐姐": []}
    for u in targets:
        groups_general[u["salutation"]].append(u["email"])
    groups_birthday = {"哥哥": {}, "姐姐": {}}
    for byear, recs in bday_groups.items():
        for r in recs:
            dct = groups_birthday[r["salutation"]]
            dct.setdefault(str(byear), []).append(r["email"])
    client = _client()
    date_cn = _ymd_cn(today)
    cache = {"date": _date_str(today), "items": []}
    for sal in ["哥哥", "姐姐"]:
        if groups_general[sal]:
            theme = (
                "节日问候"
                if holiday
                else (
                    "每月问候"
                    if is_month_start
                    else ("每周问候" if is_monday else "日常问候")
                )
            )
            messages = [
                {"role": "system", "content": prompt.system_prompt(sal)},
                {
                    "role": "user",
                    "content": prompt.general_user_prompt(
                        date_cn, sal, theme, upcoming
                    ),
                },
            ]
            text = (
                client.chat.completions.create(
                    model=_model_name(),
                    messages=messages,
                    max_tokens=4096,
                    temperature=0.7,
                    stream=False,
                )
                .choices[0]
                .message.content.strip()
            )
            jp = _json_prompt_for_image(text)
            img = _generate_image(
                jp.get("prompt", ""),
                prompt._base_negative_prompt + jp.get("negative_prompt", ""),
                "1920x1080",
            )
            _ensure_dir(os.path.join(os.getcwd(), "cache"))
            img_path = os.path.join("cache", f"general_{sal}_{_date_str(today)}.png")
            with open(img_path, "wb") as f:
                f.write(img)
            cache["items"].append(
                {
                    "type": "general",
                    "salutation": sal,
                    "recipients": groups_general[sal],
                    "subject": (
                        (holiday["name"] + "快乐！")
                        if holiday
                        else (
                            client.chat.completions.create(
                                model=_model_name(),
                                messages=prompt.generate_title_prompt(text),
                                max_tokens=4096,
                                temperature=0.7,
                                stream=False,
                            )
                            .choices[0]
                            .message.content.strip()
                        )
                    ),
                    "text": text,
                    "image_path": img_path,
                }
            )
    for sal in ["哥哥", "姐姐"]:
        dct = groups_birthday[sal]
        for byear, recs in dct.items():
            ages = []
            for u in users:
                if u["email"] in recs and u.get("birth_year"):
                    try:
                        ages.append(today.year - int(u["birth_year"]))
                    except Exception:
                        pass
            age = ages[0] if ages else 0
            messages = [
                {"role": "system", "content": prompt.system_prompt(sal)},
                {
                    "role": "user",
                    "content": prompt.birthday_user_prompt(date_cn, sal, age),
                },
            ]
            text = (
                client.chat.completions.create(
                    model=_model_name(),
                    messages=messages,
                    max_tokens=4096,
                    temperature=0.7,
                    stream=False,
                )
                .choices[0]
                .message.content.strip()
            )
            jp = _json_prompt_for_image(text)
            img = _generate_image(
                jp.get("prompt", ""), jp.get("negative_prompt", ""), "1920x1080"
            )
            _ensure_dir(os.path.join(os.getcwd(), "cache"))
            img_path = os.path.join(
                "cache", f"birthday_{sal}_{byear}_{_date_str(today)}.png"
            )
            with open(img_path, "wb") as f:
                f.write(img)
            cache["items"].append(
                {
                    "type": "birthday",
                    "salutation": sal,
                    "group": byear,
                    "recipients": recs,
                    "subject": "生日快乐！",
                    "text": text,
                    "image_path": img_path,
                }
            )
    with open(
        os.path.join("cache", f"{_date_str(today)}.json"), "w", encoding="utf-8"
    ) as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    return cache


def send_cached_for_today():
    path = os.path.join("cache", f"{_date_str(_today())}.json")
    if not os.path.isfile(path):
        return False
    with open(path, "r", encoding="utf-8") as f:
        cache = json.load(f)
    for item in cache.get("items", []):
        with open(item["image_path"], "rb") as imf:
            img = imf.read()
        _send_bcc(item["subject"], item["text"], img, item["recipients"])
    return True


if __name__ == "__main__":
    generate_today_cache()
    send_cached_for_today()
