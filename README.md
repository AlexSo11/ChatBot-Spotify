# ChatBot Spotify (Discord)

Bot de Discord que controla Spotify por comandos (`!play`, `!radio`, `!mood`, …)
y también por lenguaje natural: al mencionar al bot, Google Gemini interpreta la
petición y el bot ejecuta la acción de Spotify correspondiente.

El proyecto tiene dos piezas:

- **El bot** (`bot.py`) — se conecta a Discord y ejecuta los comandos.
- **El microservicio de auth** (`spotify_auth.py`) — resuelve el flujo OAuth de
  Spotify y guarda los tokens de cada usuario en PostgreSQL.

## Requisitos

- Python 3.10+
- Una cuenta de aplicación de Discord, una app de Spotify y una API key de Gemini.
- (Para el microservicio) una base PostgreSQL.

Instalar dependencias:

```bash
pip install -r requirements.txt
```

## Variables de entorno (`.env`)

| Variable | Usa | Descripción |
|---|---|---|
| `DISCORD_TOKEN` | bot | Token del bot de Discord |
| `SPOTIFY_CLIENT_ID` | bot + auth | Client ID de la app de Spotify |
| `SPOTIFY_CLIENT_SECRET` | bot + auth | Client Secret de la app de Spotify |
| `SPOTIFY_REDIRECT_URI` | bot + auth | URL de callback (`.../callback` del microservicio) |
| `SPOTIFY_SERVICE_URL` | bot | URL base del microservicio (default: `https://chatbot-spotify.onrender.com`) |
| `GEMINI_API_KEY` | bot | API key de Google Gemini (si falta, la IA se desactiva) |
| `GEMINI_MODEL` | bot | Modelo de Gemini (default: `gemini-2.0-flash-exp`) |
| `DATABASE_URL` | auth | Cadena de conexión PostgreSQL |
| `PORT` | auth | Puerto del microservicio (default: `3001`) |

## Ejecución

```bash
python bot.py            # inicia el bot de Discord
python spotify_auth.py   # inicia el microservicio de autenticación
```

## Estructura

```
bot.py            Punto de entrada: registra módulos y arranca el bot
config.py         Variables de entorno, cliente OAuth, instancia `bot` y helpers compartidos
events.py         Eventos de Discord (on_ready, on_command_error, on_message + despacho IA)
comandos/         Un módulo por familia de comandos (todos registran sobre `config.bot`)
  basicos.py         Login, verificación y menús de ayuda
  reproduccion.py    play, pause, resume, next, prev, song, volume
  playlists.py       Creación y gestión de playlists, radios y recomendaciones
  biblioteca.py      Búsqueda, biblioteca personal y podcasts
  descubrimiento.py  Descubrimiento de música y mixes
  social.py          Compatibilidad y ranking del servidor
  tematicas.py       Playlists temáticas (gym, estudio, viaje, romántica)
  automaticos.py     Generadores por mood y por década
  estadisticas.py    Estadísticas, historial y análisis de audio
  colaborativas.py   Playlists colaborativas y sugerencias
ia_agent.py       Integración con Gemini y memoria por usuario
spotify_auth.py   Microservicio Flask de autenticación Spotify (PostgreSQL)
```

Los comandos se definen con `@bot.command()` sobre la instancia compartida del
bot, repartidos por familias en `comandos/`. `events.on_message` es el único
punto que interpreta la respuesta de la IA.

## Notas

- La memoria de usuario (`ia_agent.py`) **se lee** para dar contexto a la IA, pero
  `_actualizar_memoria` no se llama en ningún punto, así que de momento no se
  guarda historial nuevo.
- El microservicio de auth guarda los tokens en PostgreSQL; el bot los pide por
  HTTP (`config.get_access_token_for_user`).
