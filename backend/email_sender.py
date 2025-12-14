import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr


def send_verification_email(to_email: str, code: str, action: str):
    sender = os.environ.get("SMTP_EMAIL", "")
    password = os.environ.get("SMTP_KEY", "")
    if not sender or not password:
        raise RuntimeError("SMTP_EMAIL or SMTP_KEY missing")
    subject = "YourForeverSister 验证码"
    body = f"操作：{action}\n验证码：{code}\n有效期10分钟。"
    msg = MIMEMultipart()
    msg["From"] = formataddr(["YourForeverSister", sender])
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))
    server = smtplib.SMTP_SSL(
        os.environ.get("SMTP_SERVER", ""), int(os.environ.get("SMTP_PORT", 465))
    )
    server.login(sender, password)
    server.sendmail(sender, [to_email], msg.as_string())
    server.quit()
