"""
INN lookup module using DaData API.
Free tier: 500 requests/day
Register at: https://dadata.ru/profile/#info
"""
import urllib.request
import urllib.error
import json
import threading


DADATA_URL = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/findById/party"


def lookup_inn(inn: str, token: str, callback):
    """
    Look up company by INN using DaData API.
    Calls callback(result_dict) on success, callback(None) on error.
    Result dict contains: name, inn, kpp, ogrn, address, director
    """
    def _run():
        try:
            data = json.dumps({"query": inn.strip()}).encode("utf-8")
            req = urllib.request.Request(DADATA_URL, data=data, method="POST")
            req.add_header("Content-Type", "application/json")
            req.add_header("Accept", "application/json")
            req.add_header("Authorization", f"Token {token}")

            with urllib.request.urlopen(req, timeout=8) as r:
                result = json.loads(r.read().decode("utf-8"))

            suggestions = result.get("suggestions", [])
            if not suggestions:
                callback(None)
                return

            s    = suggestions[0]
            data_s = s.get("data", {})

            # Extract director
            mgmt = data_s.get("management", {})
            director = mgmt.get("name", "") if mgmt else ""

            # Extract address
            addr = data_s.get("address", {})
            address = addr.get("value", "") if addr else ""

            info = {
                "name":      s.get("value", ""),
                "inn":       data_s.get("inn", ""),
                "kpp":       data_s.get("kpp", ""),
                "ogrn":      data_s.get("ogrn", ""),
                "address":   address,
                "director":  director,
                "phone":     "",
                "email":     "",
            }
            callback(info)

        except urllib.error.HTTPError as e:
            if e.code == 403:
                callback({"error": "Неверный API ключ DaData"})
            else:
                callback({"error": f"Ошибка API: {e.code}"})
        except Exception as e:
            callback({"error": str(e)})

    threading.Thread(target=_run, daemon=True).start()


def get_saved_token(db) -> str:
    """Get DaData token from company settings."""
    ci = db.get_active_company()
    return ci.get("dadata_token", "")


def save_token(db, token: str):
    """Save DaData token to active company settings."""
    ci = db.get_active_company()
    if ci.get("id"):
        db.update("companies", ci["id"], {"dadata_token": token})
    db.set_company_info({"dadata_token": token})
