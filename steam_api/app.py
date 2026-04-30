from flask import Flask, jsonify
import requests
import os

app = Flask(__name__)

STEAM_ID = "76561199034196805"
# Las cookies se guardan en variables de entorno — no en el código
COOKIE   = os.environ.get("STEAM_COOKIE", "")

@app.route("/steam")
def check_wishlist():
    url = (f"https://store.steampowered.com/wishlist/profiles/"
           f"{STEAM_ID}/wishlistdata/?p=0")

    headers = {
        "User-Agent":       "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0",
        "Accept":           "application/json, text/javascript, */*",
        "Accept-Encoding":  "identity",
        "Referer":          f"https://store.steampowered.com/wishlist/profiles/{STEAM_ID}/",
        "X-Requested-With": "XMLHttpRequest",
        "Cookie":           COOKIE,
    }

    try:
        r = requests.get(url, headers=headers, timeout=10)

        if r.text.strip().startswith("<"):
            return "cookie_expirada", 503

        data = r.json()
        ofertas = []

        for app_id, info in data.items():
            for sub in info.get("subs", []):
                pct = sub.get("discount_pct", 0)
                if pct > 0:
                    ofertas.append({
                        "name":     info.get("name", app_id),
                        "discount": pct
                    })

        # Respuesta ultra simple para el Pico
        return "1" if ofertas else "0"

    except Exception as e:
        return f"error:{e}", 500

# Ruta de diagnóstico — para verificar que el servidor funciona
@app.route("/ping")
def ping():
    return "pong"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)