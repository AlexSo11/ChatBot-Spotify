"""Comandos del bot: social."""

import discord

from config import bot, make_spotify_client_for_user


@bot.command()
async def compatibilidad(ctx, usuario: discord.Member):
    """Compara tu gusto musical con otro usuario"""
    if usuario.id == ctx.author.id:
        await ctx.send("❌ No puedes compararte contigo mismo.")
        return
    
    sp1 = make_spotify_client_for_user(ctx.author.id)
    sp2 = make_spotify_client_for_user(usuario.id)
    
    if not sp1:
        await ctx.send("🔴 Tú no estás logueado. Usa !login.")
        return
    if not sp2:
        await ctx.send(f"🔴 {usuario.name} no está logueado.")
        return
    
    try:
        await ctx.send(f"🔍 Comparando gustos musicales entre {ctx.author.name} y {usuario.name}...")
        
        # Obtener top artistas de ambos
        top1 = sp1.current_user_top_artists(limit=20, time_range='medium_term')
        top2 = sp2.current_user_top_artists(limit=20, time_range='medium_term')
        
        artists1 = set([a['id'] for a in top1['items']])
        artists2 = set([a['id'] for a in top2['items']])
        
        # Calcular coincidencias
        common = artists1.intersection(artists2)
        total = artists1.union(artists2)
        
        if len(total) == 0:
            await ctx.send("❌ No hay suficientes datos para comparar.")
            return
        
        compatibility = int((len(common) / len(total)) * 100)
        
        # Crear embed
        embed = discord.Embed(
            title="🤝 Compatibilidad Musical",
            color=discord.Color.purple()
        )
        
        # Meter de compatibilidad
        if compatibility >= 70:
            emoji = "💚"
            message = "¡Son almas gemelas musicales!"
        elif compatibility >= 50:
            emoji = "💛"
            message = "¡Tienen bastante en común!"
        elif compatibility >= 30:
            emoji = "🧡"
            message = "Algunos gustos compartidos"
        else:
            emoji = "💙"
            message = "Gustos muy diferentes, ¡descubran música juntos!"
        
        embed.add_field(
            name=f"{emoji} Compatibilidad",
            value=f"**{compatibility}%**\n{message}",
            inline=False
        )
        
        embed.add_field(
            name="👥 Usuarios",
            value=f"{ctx.author.mention} ↔️ {usuario.mention}",
            inline=False
        )
        
        if common:
            common_artists = []
            for artist_id in list(common)[:5]:
                for a in top1['items']:
                    if a['id'] == artist_id:
                        common_artists.append(a['name'])
                        break
            
            if common_artists:
                embed.add_field(
                    name="🎤 Artistas en común",
                    value="\n".join([f"• {a}" for a in common_artists]),
                    inline=False
                )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")
        print(f"Error en compatibilidad: {e}")

@bot.command()
async def ranking_servidor(ctx):
    """Muestra los artistas más escuchados en el servidor"""
    await ctx.send("📊 Analizando gustos del servidor...")
    
    # Contador de artistas
    artist_counts = {}
    users_analyzed = 0
    
    # Iterar por miembros del servidor
    for member in ctx.guild.members:
        if member.bot:
            continue
        
        sp = make_spotify_client_for_user(member.id)
        if not sp:
            continue
        
        try:
            top = sp.current_user_top_artists(limit=10, time_range='short_term')
            users_analyzed += 1
            
            for artist in top['items']:
                artist_id = artist['id']
                if artist_id not in artist_counts:
                    artist_counts[artist_id] = {
                        'name': artist['name'],
                        'count': 0
                    }
                artist_counts[artist_id]['count'] += 1
        except:
            continue
    
    if users_analyzed == 0:
        await ctx.send("❌ No hay suficientes usuarios con Spotify conectado.")
        return
    
    # Ordenar por popularidad
    top_artists = sorted(artist_counts.values(), key=lambda x: x['count'], reverse=True)[:10]
    
    embed = discord.Embed(
        title=f"🏆 Top Artistas de {ctx.guild.name}",
        description=f"Basado en {users_analyzed} usuarios",
        color=discord.Color.gold()
    )
    
    ranking = "\n".join([
        f"**{i+1}.** {artist['name']} - {artist['count']} {'usuario' if artist['count'] == 1 else 'usuarios'}"
        for i, artist in enumerate(top_artists)
    ])
    
    embed.add_field(name="🎤 Ranking", value=ranking, inline=False)
    
    await ctx.send(embed=embed)


# -------------------------------- Playlist Temáticas --------------------------------
