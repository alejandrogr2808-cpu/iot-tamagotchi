from flask import Flask, jsonify
import requests

app = Flask(__name__)
STEAM_ID = "76561199034196805"

@app.route("/steam")
def check_wishlist():
    url = (f"https://store.steampowered.com/wishlist/profiles/"
           f"{STEAM_ID}/wishlistdata/?p=0")
    
    # Ya no necesitamos mandar cookies falsas ni vacías
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0"
    }
    
    try:
        r = requests.get(url, headers=headers, timeout=10)
        
        # Si Steam devuelve HTML (una página de error) en lugar de JSON, 
        # significa que tu perfil o los detalles de tus juegos siguen privados.
        if r.text.strip().startswith("<"):
            return "perfil_privado", 403
            
        data = r.json()
        ofertas = []
        
        for app_id, info in data.items():
            for sub in info.get("subs", []):
                pct = sub.get("discount_pct", 0)
                if pct > 0:
                    ofertas.append({
                        "name": info.get("name", app_id),
                        "discount": pct
                    })
                    
        # Devuelve 1 si hay ofertas, 0 si no hay
        return "1" if ofertas else "0"
        
    except Exception as e:
        return f"error:{e}", 500

@app.route("/ping")
def ping():
    return "pong"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)