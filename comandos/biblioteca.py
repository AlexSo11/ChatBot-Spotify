"""Comandos del bot: biblioteca."""

from config import bot, make_spotify_client_for_user


@bot.command()
async def buscar_cancion(ctx, *, texto):
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    res = sp.search(q=texto, type="track", limit=5)
    if not res['tracks']['items']:
        await ctx.send('No encontré canciones')
        return
    msg = '**Canciones encontradas:**'
    for t in res['tracks']['items']:
        msg += f"- {t['name']} — {t['artists'][0]['name']} ({t['external_urls']['spotify']})"
    await ctx.send(msg)

@bot.command()
async def buscar_artista(ctx, *, texto):
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    res = sp.search(q=texto, type='artist', limit=5)
    if not res['artists']['items']:
        await ctx.send('No encontré artistas')
        return
    msg = '**Artistas encontrados:**'
    for a in res['artists']['items']:
        msg += f"- {a['name']} ({a['external_urls']['spotify']})"
    await ctx.send(msg)

@bot.command()
async def buscar_album(ctx, *, texto):
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    res = sp.search(q=texto, type='album', limit=5)
    if not res['albums']['items']:
        await ctx.send('No encontré álbumes')
        return
    msg = '**Álbumes encontrados:**'
    for a in res['albums']['items']:
        msg += f"- {a['name']} — {a['artists'][0]['name']} ({a['external_urls']['spotify']})"
    await ctx.send(msg)

@bot.command()
async def like(ctx, *, texto):
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    res = sp.search(q=texto, type='track', limit=1)
    if not res['tracks']['items']:
        await ctx.send('No encontré la canción')
        return
    tid = res['tracks']['items'][0]['id']
    sp.current_user_saved_tracks_add([tid])
    await ctx.send(f"Guardado: {res['tracks']['items'][0]['name']}")

@bot.command()
async def unlike(ctx, *, texto):
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    res = sp.search(q=texto, type='track', limit=1)
    if not res['tracks']['items']:
        await ctx.send('No encontré la canción')
        return
    tid = res['tracks']['items'][0]['id']
    sp.current_user_saved_tracks_delete([tid])
    await ctx.send('Eliminado')

@bot.command()
async def mislikes(ctx):
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    saved = sp.current_user_saved_tracks(limit=10)
    if not saved['items']:
        await ctx.send('No tienes canciones guardadas')
        return
    msg = '**Tus últimas canciones guardadas:**'
    for it in saved['items']:
        t = it['track']
        msg += f"- {t['name']} — {t['artists'][0]['name']}"
    await ctx.send(msg)

# ------------------- Podcasts, Playlists avanzadas y exploración -------------------

@bot.command()
async def podcast_tendencias(ctx):
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    shows = sp.search(q="podcast", type='show', limit=5)
    msg = '**Podcasts populares:**'
    for s in shows['shows']['items']:
        msg += f"- {s['name']} ({s['external_urls']['spotify']})"
    await ctx.send(msg)

@bot.command()
async def podcast_episodios(ctx, *, show):
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    res = sp.search(q=show, type='show', limit=1)
    if not res['shows']['items']:
        await ctx.send('No encontré ese podcast')
        return
    sid = res['shows']['items'][0]['id']
    eps = sp.show_episodes(sid, limit=5)
    msg = f"**Episodios de {res['shows']['items'][0]['name']}:**"
    for e in eps['items']:
        msg += f"- {e['name']} ({e['external_urls']['spotify']})"
    await ctx.send(msg)

@bot.command()
async def crear_playlist(ctx, *, nombre):
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    user = sp.current_user()['id']
    pl = sp.user_playlist_create(user, nombre, public=False)
    await ctx.send(f'Playlist creada: {pl["external_urls"]["spotify"]}')

@bot.command()
async def agregar_playlist(ctx, nombre, *, track):
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    pls = sp.current_user_playlists()
    pid = None
    for p in pls['items']:
        if p['name'].lower() == nombre.lower():
            pid = p['id']
            break
    if not pid:
        await ctx.send('No encontré esa playlist')
        return
    res = sp.search(q=track, type='track', limit=1)
    if not res['tracks']['items']:
        await ctx.send('No encontré la canción')
        return
    sp.playlist_add_items(pid, [res['tracks']['items'][0]['uri']])
    await ctx.send('Añadido')

@bot.command()
async def fusion(ctx, playlist1, playlist2):
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    def buscar(nombre):
        pls = sp.current_user_playlists()
        for p in pls['items']:
            if p['name'].lower() == nombre.lower():
                return p['id']
        return None
    p1 = buscar(playlist1)
    p2 = buscar(playlist2)
    if not p1 or not p2:
        await ctx.send('Una de las playlists no existe')
        return
    t1 = sp.playlist_items(p1)['items']
    t2 = sp.playlist_items(p2)['items']
    all_uris = list({x['track']['uri'] for x in t1 + t2})
    user = sp.current_user()['id']
    new = sp.user_playlist_create(user, f'Fusion {playlist1}+{playlist2}', public=False)
    sp.playlist_add_items(new['id'], all_uris)
    await ctx.send(f'Fusion creada: {new["external_urls"]["spotify"]}')

@bot.command()
async def limpiarplaylist(ctx, *, nombre):
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    pls = sp.current_user_playlists()
    pid = None
    for p in pls['items']:
        if p['name'].lower() == nombre.lower():
            pid = p['id']
            break
    if not pid:
        await ctx.send('No encontré esa playlist')
        return
    items = sp.playlist_items(pid)['items']
    uris = [i['track']['uri'] for i in items]
    unique = list(dict.fromkeys(uris))
    sp.playlist_replace_items(pid, unique)
    await ctx.send('Playlist limpiada')

@bot.command()
async def top_artistas(ctx):
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    res = sp.current_user_top_artists(limit=5)
    msg = '**Tus artistas más escuchados:**'
    for a in res['items']:
        msg += f"- {a['name']}"
    await ctx.send(msg)

@bot.command()
async def top_tracks(ctx):
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    res = sp.current_user_top_tracks(limit=5)
    msg = '**Tus canciones más escuchadas:**'
    for t in res['items']:
        msg += f"- {t['name']} — {t['artists'][0]['name']}"
    await ctx.send(msg)
