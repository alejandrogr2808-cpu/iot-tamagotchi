from flask import Flask, jsonify
import requests

app = Flask(__name__)
STEAM_ID = "76561199034196805"

@app.route("/steam")
def check_wishlist():
    url = (f"https://store.steampowered.com/wishlist/profiles/"
           f"{STEAM_ID}/wishlistdata/?p=0")
    
    # Camuflaje avanzado para engañar al firewall de Steam
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
        "Referer": f"https://store.steampowered.com/wishlist/profiles/{STEAM_ID}/",
        "X-Requested-With": "XMLHttpRequest",
        "Connection": "keep-alive"
    }
    
    try:
        r = requests.get(url, headers=headers, timeout=10)
        
        # Si Steam nos sigue bloqueando, esto lo imprimirá en los Logs de Render para analizarlo
        if r.text.strip().startswith("<"):
            print("STEAM BLOQUEÓ LA PETICIÓN. Respuesta:", r.text[:150])
            return "perfil_privado_o_bloqueado", 403
            
        data = r.json()
        
        # Steam devuelve una lista vacía [] si no hay juegos, o un diccionario {} si hay. 
        # Esta línea evita que el código crashee si la lista de deseados está vacía.
        if isinstance(data, list):
            return "0"
            
        ofertas = []
        for app_id, info in data.items():
            for sub in info.get("subs", []):
                pct = sub.get("discount_pct", 0)
                if pct > 0:
                    ofertas.append({
                        "name": info.get("name", app_id),
                        "discount": pct
                    })
                    
        return "1" if ofertas else "0"
        
    except Exception as e:
        return f"error:{e}", 500

@app.route("/ping")
def ping():
    return "pong"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)