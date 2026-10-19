"""Comandos del bot: colaborativas."""

import discord

from config import bot, make_spotify_client_for_user

# Estado en memoria del bot para las playlists colaborativas y sus sugerencias.
if not hasattr(bot, 'collab_playlists'):
    bot.collab_playlists = {}

if not hasattr(bot, 'playlist_suggestions'):
    bot.playlist_suggestions = {}


@bot.command()
async def colaborativa(ctx, *, nombre):
    """Crea una playlist colaborativa pública"""
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    
    try:
        user = sp.current_user()['id']
        pl = sp.user_playlist_create(user, f"🤝 {nombre}", public=True, collaborative=True)
        
        # Guardar en memoria del bot
        bot.collab_playlists[nombre.lower()] = {
            'id': pl['id'],
            'owner': ctx.author.id,
            'name': nombre,
            'url': pl['external_urls']['spotify'],
            'members': [ctx.author.id]
        }
        
        embed = discord.Embed(
            title="🤝 Playlist Colaborativa Creada",
            description=f"**{nombre}**",
            color=discord.Color.green()
        )
        
        embed.add_field(name="🔗 Link", value=pl['external_urls']['spotify'], inline=False)
        embed.add_field(name="💡 Cómo compartir", value=f"Otros usuarios pueden usar `!unirse_collab {nombre}` para colaborar", inline=False)
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")

@bot.command()
async def sugerir(ctx, playlist_nombre: str, *, cancion):
    """Sugiere una canción para una playlist colaborativa"""
    if playlist_nombre.lower() not in bot.collab_playlists:
        await ctx.send(f"❌ No existe la playlist '{playlist_nombre}'")
        return
    
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    
    try:
        # Buscar la canción
        results = sp.search(q=cancion, limit=1, type='track')
        
        if not results['tracks']['items']:
            await ctx.send(f"❌ No encontré '{cancion}'")
            return
        
        track = results['tracks']['items'][0]
        
        # Guardar sugerencia
        if playlist_nombre.lower() not in bot.playlist_suggestions:
            bot.playlist_suggestions[playlist_nombre.lower()] = []
        
        bot.playlist_suggestions[playlist_nombre.lower()].append({
            'user': ctx.author.id,
            'user_name': ctx.author.name,
            'track_uri': track['uri'],
            'track_name': track['name'],
            'artist': track['artists'][0]['name'],
            'url': track['external_urls']['spotify']
        })
        
        await ctx.send(f"✅ Sugerencia enviada: **{track['name']}** - {track['artists'][0]['name']}\nEl creador puede aceptarla con `!aceptar_sugerencia {playlist_nombre} 1`")
        
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")

@bot.command()
async def ver_sugerencias(ctx, playlist_nombre: str):
    """Ve las sugerencias de una playlist"""
    if playlist_nombre.lower() not in bot.collab_playlists:
        await ctx.send(f"❌ No existe la playlist '{playlist_nombre}'")
        return
    
    playlist_data = bot.collab_playlists[playlist_nombre.lower()]
    
    # Solo el owner puede ver sugerencias
    if ctx.author.id != playlist_data['owner']:
        await ctx.send("❌ Solo el creador de la playlist puede ver sugerencias.")
        return
    
    if playlist_nombre.lower() not in bot.playlist_suggestions or not bot.playlist_suggestions[playlist_nombre.lower()]:
        await ctx.send("📭 No hay sugerencias pendientes.")
        return
    
    suggestions = bot.playlist_suggestions[playlist_nombre.lower()]
    
    embed = discord.Embed(
        title=f"💡 Sugerencias para: {playlist_data['name']}",
        color=discord.Color.blue()
    )
    
    for i, sug in enumerate(suggestions, 1):
        embed.add_field(
            name=f"{i}. {sug['track_name']}",
            value=f"Por: {sug['artist']}\nSugerido por: {sug['user_name']}\n[Link]({sug['url']})",
            inline=False
        )
    
    embed.set_footer(text=f"Usa !aceptar_sugerencia {playlist_nombre} <número> para agregar")
    
    await ctx.send(embed=embed)

@bot.command()
async def aceptar_sugerencia(ctx, playlist_nombre: str, numero: int):
    """Acepta y agrega una sugerencia a la playlist"""
    if playlist_nombre.lower() not in bot.collab_playlists:
        await ctx.send(f"❌ No existe la playlist '{playlist_nombre}'")
        return
    
    playlist_data = bot.collab_playlists[playlist_nombre.lower()]
    
    if ctx.author.id != playlist_data['owner']:
        await ctx.send("❌ Solo el creador puede aceptar sugerencias.")
        return
    
    if playlist_nombre.lower() not in bot.playlist_suggestions:
        await ctx.send("📭 No hay sugerencias.")
        return
    
    suggestions = bot.playlist_suggestions[playlist_nombre.lower()]
    
    if numero < 1 or numero > len(suggestions):
        await ctx.send(f"❌ Número inválido. Hay {len(suggestions)} sugerencias.")
        return
    
    sp = make_spotify_client_for_user(ctx.author.id)
    if not sp:
        await ctx.send("🔴 No estás logueado. Usa !login.")
        return
    
    try:
        suggestion = suggestions[numero - 1]
        
        # Agregar a la playlist
        sp.playlist_add_items(playlist_data['id'], [suggestion['track_uri']])
        
        # Remover de sugerencias
        suggestions.pop(numero - 1)
        
        await ctx.send(f"✅ **{suggestion['track_name']}** agregada a la playlist por sugerencia de {suggestion['user_name']}")
        
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")
