import os
import json
from flask import Flask, request, redirect, jsonify
from spotipy.oauth2 import SpotifyOAuth
import time

app = Flask(__name__)
from dotenv import load_dotenv
load_dotenv()

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")

scope = (
    "user-read-private user-read-email user-top-read "
    "playlist-modify-private playlist-modify-public "
    "playlist-read-private user-read-recently-played "
    "user-read-playback-state user-modify-playback-state "
    "user-read-currently-playing user-library-read "
    "user-library-modify streaming"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(BASE_DIR, "tokens.json")

sp_oauth = SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=scope,
    open_browser=False,
    cache_path=None
)

# ----------------- Funciones -----------------
def save_token(discord_id, token):
    try:
        with open(TOKEN_FILE, "r") as f:
            data = json.load(f)
    except:
        data = {}

    data[str(discord_id)] = token
    with open(TOKEN_FILE, "w") as f:
        json.dump(data, f, indent=2)
    print(f"✅ Token guardado para usuario {discord_id}")

# ----------------- Rutas -----------------
@app.route("/")
@app.route("/login")
def login():
    discord_id = request.args.get("discord_id")
    if not discord_id:
        return "Error: No se proporcionó discord_id", 400
    auth_url = sp_oauth.get_authorize_url(state=discord_id)
    return redirect(auth_url)

@app.route("/callback")
def callback():
    code = request.args.get("code")
    discord_id = request.args.get("state")
    error = request.args.get("error")
    if error:
        return f"Error de autorización: {error}", 400
    if not code or not discord_id:
        return "Falta código o discord_id", 400

    token_info = sp_oauth.get_access_token(code, check_cache=False)
    if not token_info:
        return "No se pudo obtener token", 500

    save_token(discord_id, token_info)
    return """
    <html>
        <head><title>Login Exitoso</title></head>
        <body>
            <h1>✅ Login exitoso</h1>
            <p>Ya puedes cerrar esta ventana y usar el bot en Discord.</p>
        </body>
    </html>
    """

def refresh_token_if_needed(discord_id):
    """Devuelve access_token válido, refrescando si expiró"""
    try:
        with open(TOKEN_FILE, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        return None

    token_info = data.get(str(discord_id))
    if not token_info:
        return None

    expires_at = token_info.get("expires_at", 0)
    now = int(time.time())
    if now > expires_at - 60:  # refrescar 1 min antes de expirar
        print(f"🔄 Token expirado para {discord_id}, refrescando...")
        token_info = sp_oauth.refresh_access_token(token_info["refresh_token"])
        # Guardar de nuevo
        data[str(discord_id)] = token_info
        with open(TOKEN_FILE, "w") as f:
            json.dump(data, f, indent=2)
        print(f"✅ Token actualizado para {discord_id}")

    return token_info

@app.route("/get_token")
def get_token():
    discord_id = request.args.get("discord_id")
    if not discord_id:
        return jsonify({"error": "No discord_id provided"}), 400

    token_info = refresh_token_if_needed(discord_id)
    if not token_info:
        return jsonify({"error": "Token not found"}), 404

    return jsonify(token_info)


# ----------------- Main -----------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 3001))
    app.run(host="0.0.0.0", port=port, debug=False)
