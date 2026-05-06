from flask import Flask, jsonify
import requests

app = Flask(__name__)

# ¡TU NUEVA WISHLIST MANUAL! 
# Escribe aquí los nombres de los juegos que quieres vigilar.
# Tip: No pongas más de 5 para que el servidor responda rápido.
WISHLIST = ["Elden Ring", "Mewgenics", "Lies of P"]

@app.route("/steam")
def check_cheapshark():
    try:
        hay_ofertas = False
        
        for juego in WISHLIST:
            # Consultamos la API de CheapShark (storeID=1 significa que solo busque en Steam)
            url = f"https://www.cheapshark.com/api/1.0/deals?title={juego}&storeID=1&exact=0"
            r = requests.get(url, timeout=10)
            deals = r.json()
            
            # Revisamos si el juego tiene algún descuento (savings > 0)
            for deal in deals:
                if float(deal.get("savings", 0)) > 0:
                    hay_ofertas = True
                    break # Encontramos una oferta, no necesitamos buscar más
            
            if hay_ofertas:
                break
                
        # Devolvemos 1 si hay ofertas, 0 si no hay
        return "1" if hay_ofertas else "0"
        
    except Exception as e:
        return f"error:{e}", 500

@app.route("/ping")
def ping():
    return "pong"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)