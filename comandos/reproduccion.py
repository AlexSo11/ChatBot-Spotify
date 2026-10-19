"""Comandos del bot: reproduccion."""

from config import bot, make_spotify_client_for_user


@bot.command()
async def play(ctx, *, query):
    if query is None:
        await ctx.send("❌ Debes escribir una canción.\nEjemplo: `!play viva la vida`")
        return

    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login para conectar tu cuenta de Spotify.")
        return

    # 1. CAMBIO IMPORTANTE: Pedimos 10 resultados, no solo 1
    results = sp.search(q=query, limit=10, type="track")
    
    if not results["tracks"]["items"]:
        await ctx.send("❌ No encontré la canción.")
        return

    items = results["tracks"]["items"]
    track_to_play = items[0] # Por defecto, la primera opción (fallback)

    # 2. LÓGICA DE MEJOR COINCIDENCIA
    # Buscamos si alguna de las 10 canciones tiene el nombre EXACTO o MUY PARECIDO a lo que escribiste
    query_lower = query.lower().strip()
    
    for item in items:
        track_name = item['name'].lower()
        # Si el nombre de la canción contiene lo que escribiste (prioridad al nombre sobre la popularidad)
        if query_lower in track_name:
            track_to_play = item
            break # Encontramos una coincidencia de nombre, nos quedamos con esta

    devices = sp.devices().get("devices", [])
    if not devices:
        await ctx.send("⚠️ No hay dispositivos activos. Abre Spotify en un dispositivo y reintenta.")
        return
    
    # Usar el dispositivo activo actual o el primero de la lista
    # Intentamos buscar uno que esté activo (is_active=True)
    device_id = devices[0]["id"]
    for d in devices:
        if d['is_active']:
            device_id = d['id']
            break

    try:
        sp.start_playback(device_id=device_id, uris=[track_to_play["uri"]])
        await ctx.send(f"▶️ Reproduciendo **{track_to_play['name']}** — {track_to_play['artists'][0]['name']}")
    except Exception as e:
        await ctx.send(f"❌ Error al reproducir: {e}")

@bot.command()
async def pause(ctx):
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    try:
        sp.pause_playback()
        await ctx.send("⏸️ Pausado")
    except Exception:
        await ctx.send("⚠️ No se pudo pausar.")

@bot.command()
async def resume(ctx):
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    try:
        sp.start_playback()
        await ctx.send("▶️ Reanudado")
    except Exception:
        await ctx.send("⚠️ No se pudo reanudar.")

@bot.command()
async def next(ctx):
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    try:
        sp.next_track()
        await ctx.send("⏭️ Siguiente")
    except Exception:
        await ctx.send("⚠️ No se pudo saltar.")

@bot.command()
async def prev(ctx):
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    try:
        sp.previous_track()
        await ctx.send("⏮️ Anterior")
    except Exception:
        await ctx.send("⚠️ No se pudo regresar.")

@bot.command()
async def song(ctx):
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return

    current = sp.current_playback()
    if not current or not current.get("item"):
        await ctx.send("❌ No hay nada reproduciéndose.")
        return

    t = current["item"]
    url = t["external_urls"]["spotify"]

    await ctx.send(
        f"🎧 Sonando ahora:\n**{t['name']}** — {t['artists'][0]['name']}\n{url}"
    )

@bot.command()
async def volume(ctx, level: int):
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return

    if level < 0 or level > 100:
        await ctx.send("🔊 El volumen debe estar entre 0 y 100.")
        return

    try:
        sp.volume(level)
        await ctx.send(f"🔊 Volumen ajustado al {level}%")
    except Exception:
        await ctx.send("⚠️ No se pudo cambiar el volumen.")

# ------------------- Playlists y recomendaciones -------------------
