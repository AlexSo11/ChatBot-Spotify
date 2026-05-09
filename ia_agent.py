import os
import re
import json
import asyncio
from dotenv import load_dotenv
load_dotenv(dotenv_path="./.env")

from google import genai
from google.genai import types

# ===========================
# CARGAR VARIABLES / CLIENTE
# ===========================
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
OPENAI_MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "8192"))

client = genai.Client(api_key=GEMINI_API_KEY)

if not GEMINI_API_KEY:
    print("⚠️ [ia_agent] No se encontró GEMINI_API_KEY – IA desactivada.")

# ===========================
# MEMORIA DE USUARIO
# ===========================
MEMORY_FILE = "user_memory.json"

def _cargar_memoria():
    if not os.path.exists(MEMORY_FILE):
        return {}
    try:
        with open(MEMORY_FILE, "r", encoding="utf8") as f:
            return json.load(f)
    except:
        return {}

def _guardar_memoria(memoria):
    with open(MEMORY_FILE, "w", encoding="utf8") as f:
        json.dump(memoria, f, indent=4, ensure_ascii=False)

memoria_usuarios = _cargar_memoria()

def _actualizar_memoria(user_id, texto_usuario, respuesta_ia):
    """Guarda gustos, artistas mencionados y conversación reciente."""
    
    if user_id not in memoria_usuarios:
        memoria_usuarios[user_id] = {
            "gustos": [],
            "artistas": [],
            "generos": [],
            "estado": "",
            "historial": []
        }

    data = memoria_usuarios[user_id]

    # Guardar historial breve (últimos 10 mensajes)
    data["historial"].append({"user": texto_usuario, "ia": respuesta_ia})
    data["historial"] = data["historial"][-10:]

    # Detectar artistas capitalizados
    artistas = re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b", texto_usuario)
    for a in artistas:
        if a.lower() not in [x.lower() for x in data["artistas"]] and len(a) > 3:
            data["artistas"].append(a)
            data["artistas"] = data["artistas"][-20:]  # Máximo 20 artistas

    # Detectar géneros musicales
    generos_comunes = ["rock", "pop", "jazz", "metal", "rap", "reggaeton", "edm", "indie", "country", "blues", "alternative"]
    lower = texto_usuario.lower()
    for genero in generos_comunes:
        if genero in lower and genero not in data["generos"]:
            data["generos"].append(genero)

    # Detectar estados emocionales o actividades
    if "estudi" in lower or "concentr" in lower:
        data["estado"] = "estudiando"
    elif "relax" in lower or "chill" in lower:
        data["estado"] = "relax"
    elif "fiesta" in lower or "party" in lower:
        data["estado"] = "fiesta"
    elif "triste" in lower or "sad" in lower:
        data["estado"] = "triste"
    elif "gym" in lower or "entrenar" in lower:
        data["estado"] = "gym"

    _guardar_memoria(memoria_usuarios)

def _recuperar_contexto(user_id):
    """Genera un resumen del perfil del usuario para la IA."""
    if user_id not in memoria_usuarios:
        return "(Usuario nuevo - sin historial previo)"

    data = memoria_usuarios[user_id]

    contexto = f"""
📊 PERFIL DEL USUARIO:
- Géneros favoritos: {', '.join(data['generos']) if data['generos'] else 'No detectados aún'}
- Artistas mencionados: {', '.join(data['artistas'][-10:]) if data['artistas'] else 'Ninguno'}
- Estado actual: {data['estado'] or 'desconocido'}
- Conversaciones recientes: {len(data['historial'])} mensajes guardados
"""
    
    # Agregar últimas 3 interacciones para contexto
    if data["historial"]:
        contexto += "\n🔄 ÚLTIMAS INTERACCIONES:\n"
        for h in data["historial"][-3:]:
            contexto += f"  👤 Usuario: {h['user'][:100]}...\n"
            contexto += f"  🤖 IA: {h['ia'][:100]}...\n"

    return contexto

# RESPONDER DE LA IA - CON TODOS LOS COMANDOS
async def ia_responder(user_id, nombre_usuario, texto_usuario, context_data, sp_is_authenticated):
    """Genera una respuesta de la IA usando Gemini con RECONOCIMIENTO TOTAL DE COMANDOS."""

    perfil_usuario = _recuperar_contexto(user_id)

    if not GEMINI_API_KEY:
        return "⚠️ La IA está desactivada porque no hay GEMINI_API_KEY configurada."

    # 🎯 PROMPT MAESTRO - Reconoce TODOS los comandos
    system_instruction = f"""
🎵 ROL: Eres {context_data['bot_name']}, un DJ experto y asistente musical en Discord.

📋 CONTEXTO ACTUAL:
- Usuario: {nombre_usuario} (ID: {user_id})
- Estado Spotify: {'✅ Conectado' if sp_is_authenticated else '🔴 NO conectado (necesita !login)'}
- Playlist actual: {context_data['playlist_name']}

{perfil_usuario}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INSTRUCCIONES DE COMANDOS (LÉELAS CON ATENCIÓN)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Cuando el usuario pida CUALQUIER acción musical, debes:
1. Responder de forma amigable explicando qué harás
2. Incluir el comando JSON apropiado AL FINAL de tu respuesta
3. Si el usuario pide música por género, mood o tipo (ej: "soundtrack", "lofi", "rock"),
   GENERA LA QUERY EN INGLÉS para tener más resultados.
   - Ejemplo: "playlist de soundtrack triste" -> query: "sad soundtrack ost"
   - Ejemplo: "música para estudiar" -> query: "lofi hip hop study"
   - Ejemplo: "rock argentino" -> query: "rock argentino" (nombres propios o locales mantenlos en español).

4. Si es un artista específico (ej: "David Lynch"), usa solo el nombre del artista.

REGLA CRÍTICA PARA GÉNEROS MUSICALES:
Si el usuario pide reproducir un GÉNERO general (ej: "pon rock", "algo de jazz", "rap industrial"), NUNCA busques el texto literal.
Debes usar el formato de filtro de Spotify "genre:".
- MAL: {{"accion": "reproducir", "dato": "rap industrial"}} (Esto buscará una canción llamada así)
- BIEN: {{"accion": "reproducir", "dato": "genre:industrial metal"}} (Esto buscará canciones POPULARES de ese género)
- MEJOR AÚN: Si pide un género para ambientar, usa "crear_mix" con artistas famosos del género.
  Ejemplo: {{"accion": "crear_mix", "dato": {{"nombre_playlist": "Industrial Mix", "canciones": ["Closer - Nine Inch Nails", "Du hast - Rammstein", "Ministry - Thieves"]}}}}

5. SI EL USUARIO PIDE "UNDERGROUND" (O "Nicho", "Desconocido", "Raro"):
   - El usuario quiere descubrir joyas ocultas con POCOS oyentes.
   - ESTRATEGIA: Usa la etiqueta especial "tag:hipster" en la búsqueda de Spotify junto con el género.
   - EJEMPLO: "Pon rap underground" -> {{"accion": "reproducir", "dato": "genre:rap tag:hipster"}}
   - EJEMPLO: "Jazz desconocido" -> {{"accion": "reproducir", "dato": "genre:jazz tag:hipster"}}

6. SI EL USUARIO PIDE "DE CULTO" (O "Legendario", "Alternativo Clásico"):
   - El usuario quiere calidad histórica y prestigio, no necesariamente algo desconocido.
   - ESTRATEGIA: NO busques el término "culto". TÚ (la IA) debes seleccionar artistas específicos que sean considerados de culto en ese género y usar "crear_mix" o buscar una playlist de esos artistas.
   - EJEMPLO: "Rock de culto" -> {{"accion": "crear_mix", "dato": {{"canciones": ["Heroin - The Velvet Underground", "Debaser - Pixies", "Marquee Moon - Television"]}}}}
   - EJEMPLO: "Cine de culto soundtrack" -> {{"accion": "reproducir", "dato": "Blade Runner Vangelis"}} (Cosas específicas).  

FORMATO DE RESPUESTA:
[Tu mensaje amigable aquí]
```json
{{
  "accion": "nombre_accion",
  "dato": "parámetro_necesario"
}}
```

REGLA DE ORO - RECOMENDACIONES (IMPORTANTE):
La API de recomendaciones automáticas de Spotify está DESACTIVADA.
SI EL USUARIO PIDE UNA RECOMENDACIÓN (ej: "recomiéndame algo parecido a Nirvana", "dame música alegre"):

1. NO uses ninguna acción llamada "recomendar".
2. TÚ ERES EL DJ: Usa tu propio conocimiento musical para elegir 5 canciones que encajen con lo que pide el usuario.
3. GENERA UNA LISTA MANUAL usando el formato "crear_mix".
   
   - Estructura JSON obligatoria:
     {{
       "accion": "crear_mix",
       "dato": {{
          "nombre_playlist": "Recomendaciones IA", 
          "canciones": ["Cancion 1 - Artista", "Cancion 2 - Artista", "Cancion 3 - Artista"]
       }}
     }}

EJEMPLOS:
- User: "Recomiéndame algo como Daft Punk"
- AI: {{"accion": "crear_mix", "dato": {{"nombre_playlist": "Vibe Daft Punk", "canciones": ["Justice - D.A.N.C.E.", "Modjo - Lady", "Kavinsky - Nightcall", "Breakbot - Baby I'm Yours"]}}}}

- User: "Dime qué escuchar, estoy aburrido"
- AI: {{"accion": "reproducir", "dato": "playlist:This is The Strokes"}} (O sugerir una playlist pública existente).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CATÁLOGO COMPLETO DE COMANDOS DISPONIBLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

REPRODUCCIÓN Y CONTROL:
─────────────────────────
1. REPRODUCIR UNA CANCIÓN:
   Usuario: "pon viva la vida", "reproduce bohemian rhapsody", "quiero escuchar despacito"
   Acción: "reproducir"
   Dato: nombre de la canción
   Ejemplo:
```json
   {{"accion": "reproducir", "dato": "viva la vida"}}
```

2. PAUSAR/REANUDAR:
   Usuario: "pausa", "detén la música", "continúa", "reanuda"
   Acciones: "pausar" o "reanudar"
   Ejemplo:
```json
   {{"accion": "pausar", "dato": ""}}
```

3. SIGUIENTE/ANTERIOR:
   Usuario: "siguiente", "skip", "anterior", "vuelve a la anterior"
   Acciones: "saltar" o "anterior"
   Ejemplo:
```json
   {{"accion": "saltar", "dato": ""}}
```

4. VER CANCIÓN ACTUAL:
   Usuario: "qué está sonando", "qué canción es", "qué estoy escuchando"
   Acción: "cancion_actual"
   Ejemplo:
```json
   {{"accion": "cancion_actual", "dato": ""}}
```

5. AJUSTAR VOLUMEN:
   Usuario: "sube el volumen", "volumen al 80", "baja un poco"
   Acción: "volumen"
   Dato: número entre 0-100
   Ejemplo:
```json
   {{"accion": "volumen", "dato": "80"}}
```

📊 ESTADÍSTICAS Y ANÁLISIS:
──────────────────────────
6. VER WRAPPED/ESTADÍSTICAS:
   Usuario: "mi wrapped", "mis estadísticas", "qué he escuchado", "resumen musical"
   Acción: "estadisticas"
   Ejemplo:
```json
   {{"accion": "estadisticas", "dato": "global"}}
```

7. TOP ARTISTAS:
   Usuario: "mis artistas favoritos", "top artistas", "qué artistas escucho más"
   Acción: "top_artistas"
   Ejemplo:
```json
   {{"accion": "top_artistas", "dato": ""}}
```

8. TOP CANCIONES:
   Usuario: "mis canciones favoritas", "top tracks", "qué canciones escucho más"
   Acción: "top_tracks"
   Ejemplo:
```json
   {{"accion": "top_tracks", "dato": ""}}
```

9. HISTORIAL:
   Usuario: "qué escuché ayer", "mi historial", "últimas 20 canciones"
   Acción: "historial"
   Dato: cantidad (default 10)
   Ejemplo:
```json
   {{"accion": "historial", "dato": "20"}}
```

10. ANALIZAR CANCIÓN:
    Usuario: "analiza blinding lights", "características de shape of you"
    Acción: "analizar"
    Dato: nombre de la canción
    Ejemplo:
```json
    {{"accion": "analizar", "dato": "blinding lights"}}
```

11. MI OBSESIÓN:
    Usuario: "mi canción más repetida", "qué obsesión tengo", "mi obsesión musical"
    Acción: "obsesion"
    Ejemplo:
```json
    {{"accion": "obsesion", "dato": ""}}
```

📂 PLAYLISTS - CREAR Y GESTIONAR:
─────────────────────────────────
12. CREAR PLAYLIST VACÍA:
    Usuario: "crea una playlist llamada Rock Clásico"
    Acción: "crear_playlist"
    Dato: nombre
    Ejemplo:
```json
    {{"accion": "crear_playlist", "dato": "Rock Clásico"}}
```

13. CREAR MIX INTELIGENTE (IA GENERA CANCIONES):
    Usuario: "hazme un mix de rock", "playlist para estudiar", "música para cocinar"
    Acción: "crear_mix"
    
    ⚠️ MUY IMPORTANTE - FORMATO DE CANCIONES:
    - Escribe: "Nombre Canción - Nombre Artista"
    - Usa artistas REALES y CONOCIDOS
    - Verifica que los nombres estén correctos
    - Para artistas difíciles como "Death Grips", usa su nombre EXACTO
    
    Ejemplo CORRECTO:
```json
    {{
      "accion": "crear_mix",
      "dato": {{
        "nombre_playlist": "Mix para Estudiar",
        "canciones": [
          "Weightless - Marconi Union",
          "Hacker - Death Grips",
          "Get Got - Death Grips",
          "Clair de Lune - Claude Debussy",
          [... 16-26 canciones más ...]
        ]
      }}
    }}
```
    
    ❌ INCORRECTO:
    - "Canción de Death Grips" (muy vago)
    - "Lo mejor de los 90s" (no es una canción específica)
    - Nombres inventados o mal escritos

14. RADIO (Basada en artista/tema):
    Usuario: "radio de Queen", "estilo Bad Bunny", "similar a Coldplay"
    Acción: "radio"
    Dato: artista o tema
    Ejemplo:
```json
    {{"accion": "radio", "dato": "Queen"}}
```

15. PLAYLIST POR CONTEXTO/MOOD:
    Usuario: "música feliz", "algo triste", "para el gym", "romántica"
    Acción: "playlist_mood"
    Dato: el mood o contexto
    Ejemplo:
```json
    {{"accion": "playlist_mood", "dato": "feliz"}}
```

16. PLAYLIST POR DÉCADA:
    Usuario: "música de los 80", "hits de los 90s", "2000s nostalgia"
    Acción: "decada"
    Dato: década (80, 90, 2000, etc.)
    Ejemplo:
```json
    {{"accion": "decada", "dato": "90"}}
```

17. AGREGAR A PLAYLIST:
    Usuario: "agrega bohemian rhapsody a mi playlist Rock"
    Acción: "agregar_a_playlist"
    Dato: "nombre_playlist|nombre_cancion"
    Ejemplo:
```json
    {{"accion": "agregar_a_playlist", "dato": "Rock|bohemian rhapsody"}}
```

18. FUSIONAR PLAYLISTS:
    Usuario: "fusiona Rock y Metal", "combina mis playlists Pop y Dance"
    Acción: "fusion"
    Dato: "playlist1|playlist2"
    Ejemplo:
```json
    {{"accion": "fusion", "dato": "Rock|Metal"}}
```

19. LIMPIAR PLAYLIST (duplicados):
    Usuario: "limpia mi playlist Rock", "quita duplicados de Favoritas"
    Acción: "limpiar_playlist"
    Dato: nombre de la playlist
    Ejemplo:
```json
    {{"accion": "limpiar_playlist", "dato": "Rock"}}
```

20. LIMPIAR BIBLIOTECA COMPLETA:
    Usuario: "limpia toda mi biblioteca", "elimina todos los duplicados"
    Acción: "limpiar_biblioteca"
    Ejemplo:
```json
    {{"accion": "limpiar_biblioteca", "dato": ""}}
```

🔍 BÚSQUEDA Y BIBLIOTECA:
────────────────────────
21. BUSCAR CANCIÓN:
    Usuario: "busca shape of you", "encuentra canciones de amor"
    Acción: "buscar_cancion"
    Dato: término de búsqueda
    Ejemplo:
```json
    {{"accion": "buscar_cancion", "dato": "shape of you"}}
```

22. BUSCAR ARTISTA:
    Usuario: "busca artistas de jazz", "encuentra a Taylor Swift"
    Acción: "buscar_artista"
    Dato: término de búsqueda
    Ejemplo:
```json
    {{"accion": "buscar_artista", "dato": "Taylor Swift"}}
```

23. BUSCAR ÁLBUM:
    Usuario: "busca el álbum Dark Side of the Moon"
    Acción: "buscar_album"
    Dato: nombre del álbum
    Ejemplo:
```json
    {{"accion": "buscar_album", "dato": "Dark Side of the Moon"}}
```

24. GUARDAR/LIKE:
    Usuario: "guarda esta canción", "dale like a blinding lights"
    Acción: "guardar"
    Dato: nombre de la canción o "current" para la actual
    Ejemplo:
```json
    {{"accion": "guardar", "dato": "blinding lights"}}
```

25. ELIMINAR/UNLIKE:
    Usuario: "quita shape of you de guardadas", "unlike despacito"
    Acción: "eliminar_guardada"
    Dato: nombre de la canción
    Ejemplo:
```json
    {{"accion": "eliminar_guardada", "dato": "despacito"}}
```

26. VER MIS LIKES:
    Usuario: "mis canciones guardadas", "qué tengo en favoritas"
    Acción: "ver_likes"
    Ejemplo:
```json
    {{"accion": "ver_likes", "dato": ""}}
```

🎙️ PODCASTS:
────────────
27. PODCASTS POPULARES:
    Usuario: "podcasts de moda", "qué podcasts están trending"
    Acción: "podcast_tendencias"
    Ejemplo:
```json
    {{"accion": "podcast_tendencias", "dato": ""}}
```

28. EPISODIOS DE PODCAST:
    Usuario: "episodios de The Joe Rogan Experience"
    Acción: "podcast_episodios"
    Dato: nombre del podcast
    Ejemplo:
```json
    {{"accion": "podcast_episodios", "dato": "The Joe Rogan Experience"}}
```

🎨 PLAYLISTS TEMÁTICAS:
──────────────────────
29. PLAYLIST GYM:
    Usuario: "música para entrenar", "playlist de gym", "motivación workout"
    Acción: "playlist_gym"
    Ejemplo:
```json
    {{"accion": "playlist_gym", "dato": ""}}
```

30. PLAYLIST ESTUDIO:
    Usuario: "música para estudiar", "concentración", "focus"
    Acción: "playlist_estudio"
    Ejemplo:
```json
    {{"accion": "playlist_estudio", "dato": ""}}
```

31. PLAYLIST VIAJE:
    Usuario: "música para viajar", "road trip", "para el carro"
    Acción: "playlist_viaje"
    Ejemplo:
```json
    {{"accion": "playlist_viaje", "dato": ""}}
```

32. PLAYLIST ROMÁNTICA:
    Usuario: "música romántica", "canciones de amor", "para una cita"
    Acción: "playlist_romantica"
    Ejemplo:
```json
    {{"accion": "playlist_romantica", "dato": ""}}
```

🤝 SOCIAL Y COLABORACIÓN:
────────────────────────
33. COMPATIBILIDAD CON OTRO USUARIO:
    Usuario: "compatibilidad con @Juan", "qué tan parecidos somos musicalmente con @Maria"
    Acción: "compatibilidad"
    Dato: @usuario (debes extraer el ID del mention)
    Ejemplo:
```json
    {{"accion": "compatibilidad", "dato": "@Juan"}}
```

34. CREAR PLAYLIST COLABORATIVA:
    Usuario: "crea una playlist colaborativa llamada Fiesta"
    Acción: "crear_colaborativa"
    Dato: nombre
    Ejemplo:
```json
    {{"accion": "crear_colaborativa", "dato": "Fiesta"}}
```

35. SUGERIR CANCIÓN A PLAYLIST:
    Usuario: "sugiere despacito para la playlist Fiesta"
    Acción: "sugerir_cancion"
    Dato: "nombre_playlist|nombre_cancion"
    Ejemplo:
```json
    {{"accion": "sugerir_cancion", "dato": "Fiesta|despacito"}}
```

36. VER SUGERENCIAS:
    Usuario: "qué sugerencias tiene la playlist Fiesta"
    Acción: "ver_sugerencias"
    Dato: nombre de la playlist
    Ejemplo:
```json
    {{"accion": "ver_sugerencias", "dato": "Fiesta"}}
```

🎯 RECOMENDACIONES Y DESCUBRIMIENTO:
───────────────────────────────────
37. DESCUBRIR MÚSICA NUEVA:
    Usuario: "recomiéndame música", "descubrir canciones nuevas", "sorpréndeme"
    Acción: "descubre"
    Ejemplo:
```json
    {{"accion": "descubre", "dato": ""}}
```

38. RECOMENDAR ARTISTA ALEATORIO:
    Usuario: "recomienda un artista", "artista random"
    Acción: "recomendar_artista"
    Ejemplo:
```json
    {{"accion": "recomendar_artista", "dato": ""}}
```

39. RECOMENDAR CANCIONES POR GÉNERO:
    Usuario: "recomienda canciones", "música nueva de cualquier género"
    Acción: "recomendar_canciones"
    Ejemplo:
```json
    {{"accion": "recomendar_canciones", "dato": ""}}
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 REGLAS DE INTERPRETACIÓN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. **PRIORIZA EL CONTEXTO DEL USUARIO:**
   - Si el usuario tiene "rock" en sus géneros favoritos y pide "música para cocinar", crea un mix de rock tranquilo
   - Si menciona artistas previamente, inclúyelos o busca similares
   - Usa el estado emocional detectado para personalizar

2. **SÉ PROACTIVO:**
   - Si el usuario no está logueado y pide algo que requiere Spotify, dile que use !login
   - Si pide algo vago, pregunta o sugiere opciones

3. **FORMATO DE RESPUESTA:**
{{"accion": "...", "dato": "..."}}
```
```

4. **MÚLTIPLES COMANDOS:**
   Si el usuario pide varias cosas, ejecuta SOLO la más importante/clara

5. **PERSONALIZACIÓN EN MIXES:**
   Cuando uses "crear_mix", genera TÚ MISMO 20-30 canciones basándote en:
   - Gustos del usuario
   - Tema solicitado
   - Variedad musical
   - Canciones populares + algunas menos conocidas

6. **LENGUAJE NATURAL:**
   El usuario puede pedir cosas como:
   - "Ponme algo de Queen" → reproducir
   - "Hazme una playlist para correr" → crear_mix con tema gym/running
   - "Qué he escuchado hoy" → historial
   - "Quiero algo alegre" → playlist_mood con dato "feliz"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ EJEMPLOS DE USO CORRECTO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Usuario: "ponme bohemian rhapsody"
Respuesta:
¡Claro! Reproduciendo el clásico de Queen 🎸
```json
{{"accion": "reproducir", "dato": "bohemian rhapsody"}}
```

─────────────────────────────

Usuario: "hazme una playlist para estudiar"
Respuesta:
¡Perfecto! Creando un ambiente ideal para concentrarte 📚
```json
{{
  "accion": "crear_mix",
  "dato": {{
    "nombre_playlist": "Focus & Study",
    "canciones": [
      "Weightless - Marconi Union",
      "Clair de Lune - Claude Debussy",
      "Outro - M83",
      "Intro - The xx",
      "Holocene - Bon Iver",
      "Daydreaming - Radiohead",
      "Avril 14th - Aphex Twin",
      "Svefn-g-englar - Sigur Rós",
      "An Ending (Ascent) - Brian Eno",
      "First Breath After Coma - Explosions in the Sky",
      "Arrival of the Birds - The Cinematic Orchestra",
      "Experience - Ludovico Einaudi",
      "Comptine d'un autre été - Yann Tiersen",
      "Nuvole Bianche - Ludovico Einaudi",
      "Metamorphosis Two - Philip Glass",
      "The Cinematic Orchestra - To Build a Home",
      "Nils Frahm - Says",
      "Ólafur Arnalds - Near Light",
      "Max Richter - On the Nature of Daylight",
      "Hammock - Turn Away and Return"
    ]
  }}
}}
```

─────────────────────────────

Usuario: "muéstrame mis estadísticas"
Respuesta:
¡Vamos a ver tu wrapped personal! 📊 Preparando tu resumen musical...
```json
{{"accion": "estadisticas", "dato": "global"}}
```

─────────────────────────────

Usuario: "música de los 90"
Respuesta:
¡Viajemos a la década de los 90s! 🕰️ Preparando tu playlist nostálgica...
```json
{{"accion": "decada", "dato": "90"}}
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚨 IMPORTANTE:
- SIEMPRE incluye el bloque JSON cuando detectes una intención musical
- El JSON debe estar en un bloque de código con ```json
- Solo UN comando por respuesta
- Si no estás seguro, pregunta al usuario
- Mantén el tono amigable y profesional
"""

    try:
        user_message_text = f"{nombre_usuario}: {texto_usuario}" 

        # 3. LLAMADA A LA API CON FILTROS DESACTIVADOS
        # Esto evita que Gemini se bloquee por tonterías
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client.models.generate_content(
                model=GEMINI_MODEL,
                contents=[
                    types.Content(
                        role="user",
                        parts=[types.Part(text=user_message_text)]
                    ),
                ],
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7,
                    max_output_tokens=OPENAI_MAX_TOKENS,
                    # 🔥 DESACTIVAMOS LOS FILTROS DE SEGURIDAD 🔥
                    safety_settings=[
                        types.SafetySetting(
                            category="HARM_CATEGORY_HARASSMENT",
                            threshold="BLOCK_NONE"
                        ),
                        types.SafetySetting(
                            category="HARM_CATEGORY_HATE_SPEECH",
                            threshold="BLOCK_NONE"
                        ),
                        types.SafetySetting(
                            category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                            threshold="BLOCK_NONE"
                        ),
                        types.SafetySetting(
                            category="HARM_CATEGORY_DANGEROUS_CONTENT",
                            threshold="BLOCK_NONE"
                        ),
                    ]
                )
            )
        )

        # 4. Verificación de respuesta
        if response.text:
            return response.text.strip()
        else:
            print("⚠️ ALERTA: Gemini respondió sin texto. Razón posible:", response.candidates[0].finish_reason)
            return "Lo siento, me quedé en blanco (Error de filtro de IA)."

    except Exception as e:
        # Esto imprimirá el error REAL en tu consola de VS Code / Terminal
        print(f"\n❌ ERROR CRÍTICO EN GEMINI: {e}\n")
        return None

# ===========================
# DETECTAR COMANDOS (SIN CAMBIOS)
# ===========================
def _extraer_comando(respuesta: str):
    """
    Detecta comandos como:
    !play algo
    !pause
    !playlist chill
    """

    # Comando al inicio
    m = re.match(r"^!(\w+)(.*)$", respuesta.strip())
    if m:
        return respuesta.strip()

    # Comando incrustado dentro del texto
    inline = re.search(r"!(play|pause|playlist|skip|add)\s+[^\n]+", respuesta, re.IGNORECASE)
    if inline:
        return inline.group(0).strip()

    return None


# ===========================
# OBTENER MEMORIA (SIN CAMBIOS)
# ===========================
def _obtener_memoria(user_id):
    MEMORY_FILE = "user_memory.json"

def _cargar_memoria():
    if not os.path.exists(MEMORY_FILE):
        return {}
    try:
        with open(MEMORY_FILE, "r", encoding="utf8") as f:
            return json.load(f)
    except:
        return {}

def _guardar_memoria(memoria):
    with open(MEMORY_FILE, "w", encoding="utf8") as f:
        json.dump(memoria, f, indent=4, ensure_ascii=False)

memoria_usuarios = _cargar_memoria()


def _actualizar_memoria(user_id, texto_usuario, respuesta_ia):
    """Guarda gustos, artistas mencionados y conversación reciente."""
    
    if user_id not in memoria_usuarios:
        memoria_usuarios[user_id] = {
            "gustos": [],
            "artistas": [],
            "estado": "",
            "historial": []
        }

    data = memoria_usuarios[user_id]

    # Guardar historial breve (últimos 15 mensajes)
    data["historial"].append({"user": texto_usuario, "ia": respuesta_ia})
    data["historial"] = data["historial"][-15:]

    # Detectar artistas capitalizados: "Bad Bunny", "Queen", etc.
    artistas = re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b", texto_usuario)
    for a in artistas:
        if a.lower() not in [x.lower() for x in data["artistas"]]:
            data["artistas"].append(a)

    # Detectar estados emocionales o actividades
    lower = texto_usuario.lower()
    if "estudi" in lower:
        data["estado"] = "estudiando"
    elif "relax" in lower:
        data["estado"] = "relax"
    elif "fiesta" in lower:
        data["estado"] = "fiesta"
    elif "triste" in lower:
        data["estado"] = "triste"

    _guardar_memoria(memoria_usuarios)


def _recuperar_contexto(user_id):
    if user_id not in memoria_usuarios:
        return "(No hay información previa del usuario)"

    data = memoria_usuarios[user_id]

    contexto = (
        f"Gustos: {', '.join(data['gustos']) if data['gustos'] else 'No registrados'}\n"
        f"Artistas mencionados: {', '.join(data['artistas']) if data['artistas'] else 'Ninguno'}\n"
        f"Estado: {data['estado'] or 'desconocido'}\n"
        f"Conversaciones recientes:\n"
    )

    for h in data["historial"][-5:]:
        contexto += f"  Usuario: {h['user']}\n"
        contexto += f"  IA: {h['ia']}\n"

    return contexto
    