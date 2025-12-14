import time
import secrets

_store: dict[tuple[str, str], dict[str, float | str]] = {}
_ttl_seconds = 600


def generate_code(email: str, action: str) -> str:
    code = "".join(secrets.choice("0123456789") for _ in range(6))
    _store[(email, action)] = {"code": code, "expire": time.time() + _ttl_seconds}
    return code


def verify_code(email: str, action: str, code: str) -> bool:
    item = _store.get((email, action))
    if not item:
        return False
    if time.time() > float(item["expire"]):
        _store.pop((email, action), None)
        return False
    ok = str(item["code"]) == str(code)
    if ok:
        _store.pop((email, action), None)
    return ok
