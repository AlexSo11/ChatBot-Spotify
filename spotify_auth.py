import os
import json
import time
from flask import Flask, request, redirect, jsonify
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# ----------------- Config -----------------
load_dotenv()

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")
DATABASE_URL = os.getenv("DATABASE_URL")

SCOPE = (
    "user-read-private user-read-email user-top-read "
    "playlist-modify-private playlist-modify-public "
    "playlist-read-private user-read-recently-played "
    "user-read-playback-state user-modify-playback-state "
    "user-read-currently-playing user-library-read "
    "user-library-modify streaming"
)

sp_oauth = SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=SCOPE,
    open_browser=False,
    cache_path=None
)

app = Flask(__name__)

# ----------------- Database Functions -----------------
def get_db_connection():
    """Conexión a PostgreSQL"""
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        return conn
    except Exception as e:
        print(f"❌ Error conectando a DB: {e}")
        return None

def init_db():
    """Crea la tabla si no existe"""
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS spotify_tokens (
                discord_id VARCHAR(50) PRIMARY KEY,
                access_token TEXT NOT NULL,
                refresh_token TEXT NOT NULL,
                expires_at BIGINT NOT NULL,
                token_type VARCHAR(20),
                scope TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        print("✅ Tabla spotify_tokens verificada/creada")
    except Exception as e:
        print(f"❌ Error creando tabla: {e}")
    finally:
        cur.close()
        conn.close()

def save_token(discord_id, token_info):
    """Guarda o actualiza token en PostgreSQL"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO spotify_tokens 
            (discord_id, access_token, refresh_token, expires_at, token_type, scope, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (discord_id) 
            DO UPDATE SET 
                access_token = EXCLUDED.access_token,
                refresh_token = EXCLUDED.refresh_token,
                expires_at = EXCLUDED.expires_at,
                updated_at = CURRENT_TIMESTAMP
        """, (
            str(discord_id),
            token_info['access_token'],
            token_info['refresh_token'],
            token_info['expires_at'],
            token_info.get('token_type', 'Bearer'),
            token_info.get('scope', SCOPE)
        ))
        conn.commit()
        print(f"✅ Token guardado para usuario {discord_id}")
        return True
    except Exception as e:
        print(f"❌ Error guardando token: {e}")
        return False
    finally:
        cur.close()
        conn.close()

def get_token(discord_id):
    """Obtiene token desde PostgreSQL"""
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT access_token, refresh_token, expires_at, token_type, scope
            FROM spotify_tokens 
            WHERE discord_id = %s
        """, (str(discord_id),))
        
        result = cur.fetchone()
        
        if result:
            return dict(result)
        return None
    except Exception as e:
        print(f"❌ Error obteniendo token: {e}")
        return None
    finally:
        cur.close()
        conn.close()

def refresh_token_if_needed(discord_id):
    """Devuelve access_token válido, refrescando si expiró"""
    token_info = get_token(discord_id)
    if not token_info:
        return None

    expires_at = token_info.get("expires_at", 0)
    now = int(time.time())

    # Si el token está por expirar o ya expiró
    if now > expires_at - 60:
        print(f"🔄 Token expirado para {discord_id}, refrescando...")
        try:
            new_token = sp_oauth.refresh_access_token(token_info["refresh_token"])
            save_token(discord_id, new_token)
            print(f"✅ Token actualizado para {discord_id}")
            return new_token
        except Exception as e:
            print(f"❌ Error al refrescar token: {e}")
            return None

    return token_info

def get_all_users():
    """Obtiene lista de usuarios autenticados"""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT discord_id, created_at, updated_at FROM spotify_tokens ORDER BY updated_at DESC")
        users = cur.fetchall()
        return users
    except Exception as e:
        print(f"❌ Error obteniendo usuarios: {e}")
        return []
    finally:
        cur.close()
        conn.close()

# ----------------- Rutas -----------------
@app.route("/")
def home():
    users = get_all_users()
    return {
        "service": "Spotify Auth Service",
        "status": "running",
        "database": "PostgreSQL",
        "authenticated_users": len(users)
    }

@app.route("/login")
def login():
    discord_id = request.args.get("discord_id")
    if not discord_id:
        return "Error: No se proporcionó discord_id", 400

    auth_url = sp_oauth.get_authorize_url(state=discord_id)
    print(f"🔗 Login solicitado para {discord_id}")
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

    try:
        token_info = sp_oauth.get_access_token(code, check_cache=False)
    except Exception as e:
        print(f"❌ Error al obtener token: {e}")
        return f"Error al obtener token: {e}", 500

    if not token_info:
        return "No se pudo obtener token", 500

    if save_token(discord_id, token_info):
        return """
        <html>
            <head>
                <title>Login Exitoso</title>
                <style>
                    body { 
                        font-family: 'Segoe UI', Arial, sans-serif; 
                        text-align: center; 
                        padding: 50px;
                        background: linear-gradient(135deg, #1DB954 0%, #191414 100%);
                        color: white;
                    }
                    h1 { color: #1DB954; font-size: 3em; }
                    p { font-size: 1.2em; }
                </style>
            </head>
            <body>
                <h1>✅ Login exitoso</h1>
                <p>Tu cuenta de Spotify está conectada al bot de Discord.</p>
                <p>Ya puedes cerrar esta ventana y usar los comandos en Discord.</p>
            </body>
        </html>
        """
    else:
        return "Error guardando el token", 500

@app.route("/get_token")
def get_token_route():
    """Endpoint que consulta el bot"""
    discord_id = request.args.get("discord_id")
    if not discord_id:
        return jsonify({"error": "No discord_id provided"}), 400

    print(f"📡 Bot consultando token para {discord_id}")
    
    token_info = refresh_token_if_needed(discord_id)
    if not token_info:
        print(f"❌ Token no encontrado para {discord_id}")
        return jsonify({"error": "Token not found"}), 404

    print(f"✅ Token enviado para {discord_id}")
    return jsonify(token_info)

@app.route("/health")
def health():
    """Health check para Render"""
    conn = get_db_connection()
    db_status = "connected" if conn else "disconnected"
    if conn:
        conn.close()
    
    return {
        "status": "healthy",
        "database": db_status,
        "authenticated_users": len(get_all_users())
    }, 200

@app.route("/debug/users")
def debug_users():
    """Ver usuarios autenticados (solo para debugging)"""
    users = get_all_users()
    return {
        "total": len(users),
        "users": [{"discord_id": u[0], "created_at": str(u[1]), "updated_at": str(u[2])} for u in users]
    }

# ----------------- Main -----------------
if __name__ == "__main__":
    print("🔌 Conectando a PostgreSQL...")
    init_db()
    
    port = int(os.getenv("PORT", 3001))
    print(f"🚀 Servidor SpotifyAuth corriendo en 0.0.0.0:{port}")
    print(f"💾 Almacenamiento: PostgreSQL (persistente)")
    app.run(host="0.0.0.0", port=port, debug=False)