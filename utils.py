# © VEGA — Intellectual Property Rights

# Respect for Copyright and Content Protection

# In this project, we are committed to respecting community laws, protecting intellectual property rights, and appreciating the efforts of all creators and content owners.

# "All rights are reserved to their original owners, and this project does not constitute a waiver of any intellectual property rights belonging to other parties.

# © VEGA — All rights related to this project are reserved to their owners."

# Supporting Creators is a Responsibility

# - Creativity is the fruit of effort that deserves appreciation and respect.
# - Protecting copyright contributes to building a more just digital community.
# - Usage licenses and redistribution terms must be respected.
# - We reject unauthorized use of any content protected by copyright.

# Responsible Use Pledge

# By using this project, you pledge to respect intellectual property rights and not to copy or redistribute any protected content without obtaining the necessary permission or license.

# Be a partner in protecting creativity, and do not be a cause of rights violations.

# © VEGA | By: @TopVeGa All Rights Reserved


import requests
import base64
import re
import random
import logging
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from config import API_BASE

logger = logging.getLogger(__name__)


def _make_session():
    s = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    s.mount("https://", HTTPAdapter(max_retries=retry))
    return s


_session = _make_session()


def smart_random_string(length):
    vowels = "aeiou"
    consonants = "bcdfghjklmnpqrstvwxyz"
    out = ""
    while len(out) < length:
        out += random.choice(consonants) if len(out) % 2 == 0 else random.choice(vowels)
    return out[:length]


def create_bot_email(user_id):
    from database import add_mailbox, can_create_mailbox
    ok, msg = can_create_mailbox(user_id)
    if not ok:
        return None, msg, None, None

    try:
        addrs = smart_random_string(8)
        paswd = smart_random_string(8)

        domains = _session.get(f"{API_BASE}/domains", timeout=10).json()
        domain = next((d["domain"] for d in domains.get("hydra:member", []) if d.get("isActive")), None)
        if not domain:
            return None, "لا يوجد نطاق متاح حالياً.", None, None

        address = f"{addrs}@{domain}"
        headers = {"Content-type": "application/json"}
        params = {"address": address, "password": paswd}

        acc = _session.post(f"{API_BASE}/accounts", json=params, headers=headers, timeout=10).json()
        if "id" not in acc:
            return None, f"فشل إنشاء الحساب: {acc.get('message', '')}", None, None

        tok = _session.post(f"{API_BASE}/token", json=params, headers=headers, timeout=10).json()
        token = tok.get("token", "")
        if not token:
            return None, "فشل الحصول على التوكن.", None, None

        add_mailbox(user_id, address, paswd, token, domain)
        return address, paswd, token, domain
    except Exception as e:
        logger.error(f"create_bot_email: {e}")
        return None, "حدث خطأ غير متوقع.", None, None


def decode_mime(text):
    parts = re.findall(
        r'Content-Type: text/plain; charset=utf-8\r\nContent-Transfer-Encoding: base64\r\n\r\n(.*?)--',
        text, re.DOTALL
    )
    out = []
    for p in parts:
        try:
            out.append(re.sub(r"<.*?>", "", base64.b64decode(p).decode("utf-8", errors="ignore")))
        except Exception:
            continue
    return "\n".join(out)


def fetch_inbox(token):
    try:
        headers = {"Authorization": f"Bearer {token}"}
        res = _session.get(f"{API_BASE}/messages", headers=headers, timeout=10).json()
        if res.get("hydra:totalItems", 0) == 0:
            return False, "صندوق الوارد فارغ."

        msgs = []
        for m in res.get("hydra:member", []):
            frm = m.get("from", {})
            sender = f"من {frm.get('name', '')}\n{frm.get('address', '')}\n\n"
            subj = f"{m.get('subject', 'بدون موضوع')}\n"
            try:
                body = decode_mime(_session.get(f"{API_BASE}{m['downloadUrl']}", headers=headers, timeout=10).text)
            except Exception:
                body = "[تعذر جلب المحتوى]"
            msgs.append(sender + subj + body)
        return True, msgs
    except Exception as e:
        logger.error(f"fetch_inbox: {e}")
        return False, "حدث خطأ أثناء جلب الوارد."


def get_message_count(token):
    try:
        headers = {"Authorization": f"Bearer {token}"}
        res = _session.get(f"{API_BASE}/messages", headers=headers, timeout=10).json()
        return res.get("hydra:totalItems", 0)
    except Exception:
        return -1


def change_password(token, new_password):
    try:
        headers = {"Authorization": f"Bearer {token}", "Content-type": "application/json"}
        res = _session.patch(f"{API_BASE}/me", json={"password": new_password}, headers=headers, timeout=10)
        return res.status_code in (200, 204), res.text
    except Exception as e:
        return False, str(e)


def refresh_token(address, password):
    try:
        res = _session.post(f"{API_BASE}/token", json={"address": address, "password": password}, timeout=10).json()
        return res.get("token"), res
    except Exception as e:
        return None, str(e)


def delete_remote_account(token):
    try:
        headers = {"Authorization": f"Bearer {token}"}
        res = _session.delete(f"{API_BASE}/accounts/me", headers=headers, timeout=10)
        return res.status_code in (200, 204)
    except Exception:
        return False


def set_account_enabled(token, enabled):
    return True