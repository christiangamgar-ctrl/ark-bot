import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import asyncio
from datetime import datetime

# ─── CONFIG ───────────────────────────────────────────────────────────────────
TOKEN = os.environ.get("DISCORD_TOKEN", "TU_TOKEN_AQUI")
DATA_FILE = "data.json"

# ─── CUEVAS FJORDUR ───────────────────────────────────────────────────────────
CUEVAS_DIFICIL = {
    "Lab Cave":        (10, 15),
    "Swamp Cave":      (8,  12),
    "Bee Cave":        (10, 15),
    "Cave 88/15":      (8,  15),
}
CUEVAS_MEDIA = {
    "Cave 10/60":         (5, 5),
    "Cave 60/80":         (5, 5),
    "Cave 10/49":         (3, 5),
    "Big Ice Cave 08/23": (5, 8),
    "Small Lava 21/57":   (5, 8),
    "Darth Cave 29/39":   (5, 8),
    "Big Uw Cave 76/65":  (5, 8),
}
CUEVAS_FACIL = {
    "Cave 20/10":     (2, 4),
    "Cave 30/40":     (2, 4),
    "Cave 45/63":     (3, 5),
    "Big Lava 91/78": (3, 5),
}
TODAS_CUEVAS = {**CUEVAS_DIFICIL, **CUEVAS_MEDIA, **CUEVAS_FACIL}

# ─── DATOS ────────────────────────────────────────────────────────────────────
def cargar_datos():
    if not os.path.exists(DATA_FILE):
        return {"tribus": {}, "solicitudes_pendientes": [], "log_channel": None,
                "tribus_channel": None, "marcador_channel": None, "marcador_message_id": None}
    datos = json.load(open(DATA_FILE, "r", encoding="utf-8"))
    datos.setdefault("tribus_channel", None)
    datos.setdefault("marcador_channel", None)
    datos.setdefault("marcador_message_id", None)
    return datos

def guardar_datos(datos):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=2, ensure_ascii=False)

# ─── BOT SETUP ────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ─── HELPERS ──────────────────────────────────────────────────────────────────
def es_admin(interaction: discord.Interaction) -> bool:
    return interaction.user.guild_permissions.administrator or \
           any(r.name.lower() in ["admin", "administrador", "moderador", "mod"]
               for r in interaction.user.roles)

def es_lider(interaction: discord.Interaction, datos) -> str | None:
    uid = str(interaction.user.id)
    for nombre, tribu in datos["tribus"].items():
        if tribu["lider_id"] == uid:
            return nombre
    return None

def embed_base(titulo, descripcion="", color=0x00b4d8):
    embed = discord.Embed(title=f"🦕 {titulo}", description=descripcion, color=color)
    embed.set_footer(text="ARK Survival Evolved • Fjordur PS4")
    return embed

async def notificar_log(guild, mensaje):
    datos = cargar_datos()
    ch_id = datos.get("log_channel")
    if ch_id:
        ch = guild.get_channel(int(ch_id))
        if ch:
            await ch.send(mensaje)

def build_embed_tribu(nombre, t):
    embed = discord.Embed(title=f"🏕️ {t['tag']} {nombre}", color=0x00b4d8)
    embed.set_footer(text="ARK Survival Evolved • Fjordur PS4")
    embed.add_field(name="👑 Líder Discord", value=f"<@{t['lider_id']}>", inline=True)
    embed.add_field(name="🏆 Puntos", value=f"**{t['puntos']}**", inline=True)
    embed.add_field(name="⚔️ Raids", value=str(len(t["raids"])), inline=True)
    discord_ids = t.get("discord_ids", {})
    miembros_lineas = []
    for i, psn in enumerate(t["miembros_psn"]):
        did = discord_ids.get(str(i))
        miembros_lineas.append(f"🎮 `{psn}`" + (f" — <@{did}>" if did else ""))
    embed.add_field(
        name=f"👥 Miembros ({len(t['miembros_psn'])}/6)",
        value="\n".join(miembros_lineas) or "Sin miembros",
        inline=False
    )
    embed.add_field(name="📅 Registrada", value=t["fecha_registro"], inline=True)
    return embed

async def actualizar_embed_tribu(guild, nombre_tribu):
    datos = cargar_datos()
    ch_id = datos.get("tribus_channel")
    if not ch_id:
        return
    ch = guild.get_channel(int(ch_id))
    if not ch:
        return
    t = datos["tribus"].get(nombre_tribu)
    if not t:
        return
    embed = build_embed_tribu(nombre_tribu, t)
    msg_id = t.get("mensaje_id")
    if msg_id:
        try:
            msg = await ch.fetch_message(int(msg_id))
            await msg.edit(embed=embed)
            return
        except:
            pass
    msg = await ch.send(embed=embed)
    datos["tribus"][nombre_tribu]["mensaje_id"] = str(msg.id)
    guardar_datos(datos)

async def actualizar_marcador(guild):
    datos = cargar_datos()
    ch_id = datos.get("marcador_channel")
    if not ch_id or not datos["tribus"]:
        return
    ch = guild.get_channel(int(ch_id))
    if not ch:
        return
    sorted_tribus = sorted(datos["tribus"].items(), key=lambda x: x[1]["puntos"], reverse=True)
    medallas = ["🥇", "🥈", "🥉"]
    desc = ""
    for i, (nombre, t) in enumerate(sorted_tribus):
        medalla = medallas[i] if i < 3 else f"`#{i+1}`"
        desc += f"{medalla} **{t['tag']} {nombre}** — **{t['puntos']} pts** ({len(t['raids'])} raids)\n"
    embed = discord.Embed(title="🏆 Alpha Cluster Ranking — Fjordur PS4", description=desc, color=0xffd700)
    embed.set_footer(text="ARK Survival Evolved • Fjordur PS4")
    embed.add_field(name="📅 Actualizado", value=datetime.now().strftime("%d/%m/%Y %H:%M"), inline=True)
    embed.add_field(name="🏕️ Tribus activas", value=str(len(datos["tribus"])), inline=True)
    msg_id = datos.get("marcador_message_id")
    if msg_id:
        try:
            msg = await ch.fetch_message(int(msg_id))
            await msg.edit(embed=embed)
            return
        except:
            pass
    msg = await ch.send(embed=embed)
    datos["marcador_message_id"] = str(msg.id)
    guardar_datos(datos)

# ═══════════════════════════════════════════════════════════════════════════════
#  SLASH COMMANDS
# ═══════════════════════════════════════════════════════════════════════════════

@bot.tree.command(name="registrar-tribu", description="Registra tu tribu en el servidor")
@app_commands.describe(
    nombre="Nombre de la tribu",
    tag="Tag de la tribu (ej: [ARK])",
    miembros_psn="PSN IDs separados por comas",
    discord_ids="IDs de Discord separados por comas (mismo orden que PSN)",
    nombre_cueva="Nombre de la cueva base",
    coordenadas="Coordenadas de la cueva base (ej: 35.2 / 56.8)"
)
async def registrar_tribu(interaction: discord.Interaction, nombre: str, tag: str,
                           miembros_psn: str, discord_ids: str,
                           nombre_cueva: str, coordenadas: str):
    datos = cargar_datos()
    tribu_actual = es_lider(interaction, datos)
    if tribu_actual:
        await interaction.response.send_message(
            embed=embed_base("❌ Error", f"Ya eres líder de **{tribu_actual}**.", 0xff4444), ephemeral=True)
        return
    if nombre.lower() in [t.lower() for t in datos["tribus"]]:
        await interaction.response.send_message(
            embed=embed_base("❌ Error", f"Ya existe una tribu llamada **{nombre}**.", 0xff4444), ephemeral=True)
        return
    lista_psn = [m.strip() for m in miembros_psn.split(",") if m.strip()]
    lista_discord = [d.strip().strip("<@>").strip("!") for d in discord_ids.split(",") if d.strip()]
    if len(lista_psn) < 1 or len(lista_psn) > 6:
        await interaction.response.send_message(
            embed=embed_base("❌ Error", "Las tribus deben tener entre 1 y 6 miembros.", 0xff4444), ephemeral=True)
        return
    if len(lista_psn) != len(lista_discord):
        await interaction.response.send_message(
            embed=embed_base("❌ Error",
                f"El nº de PSN IDs ({len(lista_psn)}) y Discord IDs ({len(lista_discord)}) debe coincidir.", 0xff4444),
            ephemeral=True)
        return
    discord_ids_map = {str(i): lista_discord[i] for i in range(len(lista_discord))}
    solicitud = {
        "tipo": "registro_tribu",
        "id": datetime.now().strftime("%Y%m%d%H%M%S"),
        "nombre": nombre, "tag": tag,
        "lider_id": str(interaction.user.id),
        "lider_discord": interaction.user.display_name,
        "miembros_psn": lista_psn,
        "discord_ids": discord_ids_map,
        "nombre_cueva": nombre_cueva,
        "coordenadas": coordenadas,
        "fecha": datetime.now().strftime("%d/%m/%Y %H:%M")
    }
    datos["solicitudes_pendientes"].append(solicitud)
    guardar_datos(datos)
    miembros_txt = "\n".join([f"🎮 `{lista_psn[i]}` — <@{lista_discord[i]}>" for i in range(len(lista_psn))])
    embed = embed_base("✅ Solicitud enviada",
        f"Tu tribu **{nombre}** [{tag}] está **pendiente de aprobación**.\n\n"
        f"**Miembros ({len(lista_psn)}/6):**\n{miembros_txt}\n\n"
        f"🗺️ {nombre_cueva} | 📍 `{coordenadas}`", 0xffa500)
    await interaction.response.send_message(embed=embed, ephemeral=True)
    await notificar_log(interaction.guild,
        f"📋 Nueva solicitud: **{nombre}** [{tag}] por {interaction.user.mention} — {len(lista_psn)} miembros")

@bot.tree.command(name="aprobar-tribu", description="[ADMIN] Aprueba o rechaza una solicitud de tribu")
@app_commands.describe(id_solicitud="ID de la solicitud", accion="aprobar o rechazar")
@app_commands.choices(accion=[
    app_commands.Choice(name="Aprobar", value="aprobar"),
    app_commands.Choice(name="Rechazar", value="rechazar"),
])
async def aprobar_tribu(interaction: discord.Interaction, id_solicitud: str, accion: str):
    if not es_admin(interaction):
        await interaction.response.send_message(
            embed=embed_base("❌ Sin permisos", "Solo los admins pueden usar este comando.", 0xff4444), ephemeral=True)
        return
    datos = cargar_datos()
    sol = next((s for s in datos["solicitudes_pendientes"]
                if s["id"] == id_solicitud and s["tipo"] == "registro_tribu"), None)
    if not sol:
        await interaction.response.send_message(
            embed=embed_base("❌ Error", f"No se encontró la solicitud `{id_solicitud}`.", 0xff4444), ephemeral=True)
        return
    datos["solicitudes_pendientes"].remove(sol)
    if accion == "aprobar":
        datos["tribus"][sol["nombre"]] = {
            "tag": sol["tag"],
            "lider_id": sol["lider_id"],
            "lider_discord": sol["lider_discord"],
            "miembros_psn": sol["miembros_psn"],
            "discord_ids": sol.get("discord_ids", {}),
            "nombre_cueva": sol.get("nombre_cueva", "No especificada"),
            "coordenadas": sol.get("coordenadas", "No especificadas"),
            "puntos": 0, "raids": [], "mensaje_id": None,
            "fecha_registro": sol["fecha"]
        }
        guardar_datos(datos)
        await actualizar_embed_tribu(interaction.guild, sol["nombre"])
        await actualizar_marcador(interaction.guild)
        await interaction.response.send_message(
            embed=embed_base("✅ Tribu aprobada",
                f"**{sol['nombre']}** [{sol['tag']}] aprobada y publicada en el canal de tribus.", 0x00ff88),
            ephemeral=True)
        lider = interaction.guild.get_member(int(sol["lider_id"]))
        if lider:
            try:
                await lider.send(embed=embed_base("🎉 ¡Tribu aprobada!",
                    f"Tu tribu **{sol['nombre']}** ha sido aprobada en el servidor ARK Fjordur PS4."))
            except:
                pass
        await notificar_log(interaction.guild, f"✅ Tribu **{sol['nombre']}** aprobada por {interaction.user.mention}")
    else:
        guardar_datos(datos)
        await interaction.response.send_message(
            embed=embed_base("❌ Tribu rechazada", f"Solicitud de **{sol['nombre']}** rechazada.", 0xff4444),
            ephemeral=True)
        await notificar_log(interaction.guild, f"❌ Tribu **{sol['nombre']}** rechazada por {interaction.user.mention}")

@bot.tree.command(name="solicitudes-pendientes", description="[ADMIN] Ver todas las solicitudes pendientes")
async def solicitudes_pendientes(interaction: discord.Interaction):
    if not es_admin(interaction):
        await interaction.response.send_message(
            embed=embed_base("❌ Sin permisos", "Solo los admins pueden usar este comando.", 0xff4444), ephemeral=True)
        return
    datos = cargar_datos()
    solic = datos["solicitudes_pendientes"]
    if not solic:
        await interaction.response.send_message(
            embed=embed_base("📋 Solicitudes", "No hay solicitudes pendientes."), ephemeral=True)
        return
    embed = embed_base("📋 Solicitudes Pendientes", f"Total: **{len(solic)}**", 0xffa500)
    for s in solic:
        if s["tipo"] == "registro_tribu":
            discord_ids = s.get("discord_ids", {})
            psns = s["miembros_psn"]
            miembros_txt = "\n".join([f"🎮 `{psns[int(k)]}` — <@{v}>" for k, v in discord_ids.items()]) if discord_ids else ", ".join(psns)
            embed.add_field(
                name=f"[{s['id']}] 🏕️ {s['nombre']} [{s['tag']}]",
                value=f"👑 {s['lider_discord']}\n{miembros_txt}\n"
                      f"🗺️ {s.get('nombre_cueva','N/A')} | 📍 `{s.get('coordenadas','N/A')}`\n"
                      f"📅 {s['fecha']}\n"
                      f"✅ `/aprobar-tribu {s['id']} aprobar` | ❌ `/aprobar-tribu {s['id']} rechazar`",
                inline=False)
        elif s["tipo"] == "raid":
            embed.add_field(
                name=f"[{s['id']}] ⚔️ Raid de {s['tribu']}",
                value=f"🗺️ {s['cueva']} | 🏆 {s['puntos']} pts\n"
                      f"📝 {s.get('notas','Sin notas')} | 📅 {s['fecha']}\n"
                      f"✅ `/aprobar-raid {s['id']} aprobar` | ❌ `/aprobar-raid {s['id']} rechazar`",
                inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="añadir-raid", description="Registra una raid completada por tu tribu")
@app_commands.describe(
    tipo_cueva="Puntos fijos o variables",
    cueva="Nombre de la cueva (usa /cuevas para ver la lista)",
    dificultad="Normal o Hard (cuevas fijas)",
    puntos_variables="Puntos si es cueva variable",
    notas="Notas adicionales (opcional)"
)
@app_commands.choices(tipo_cueva=[
    app_commands.Choice(name="Cueva con puntos fijos", value="fija"),
    app_commands.Choice(name="Cueva con puntos variables", value="variable"),
])
@app_commands.choices(dificultad=[
    app_commands.Choice(name="Normal", value="normal"),
    app_commands.Choice(name="Hard", value="hard"),
])
async def añadir_raid(interaction: discord.Interaction, tipo_cueva: str, cueva: str,
                       dificultad: str = "normal", puntos_variables: int = 0, notas: str = ""):
    datos = cargar_datos()
    nombre_tribu = es_lider(interaction, datos)
    if not nombre_tribu:
        await interaction.response.send_message(
            embed=embed_base("❌ Error", "Solo los líderes pueden registrar raids.", 0xff4444), ephemeral=True)
        return
    if tipo_cueva == "fija":
        match = next((k for k in TODAS_CUEVAS if cueva.lower() in k.lower()), None)
        if not match:
            await interaction.response.send_message(
                embed=embed_base("❌ Cueva no encontrada", "Usa `/cuevas` para ver la lista completa.", 0xff4444),
                ephemeral=True)
            return
        cueva_display = match
        pts_n, pts_h = TODAS_CUEVAS[match]
        puntos = pts_h if dificultad == "hard" else pts_n
    else:
        if puntos_variables <= 0:
            await interaction.response.send_message(
                embed=embed_base("❌ Error", "Indica los puntos para una cueva variable.", 0xff4444), ephemeral=True)
            return
        cueva_display = cueva
        puntos = puntos_variables
    solicitud = {
        "tipo": "raid", "id": datetime.now().strftime("%Y%m%d%H%M%S"),
        "tribu": nombre_tribu, "cueva": cueva_display,
        "dificultad": dificultad, "puntos": puntos,
        "tipo_cueva": tipo_cueva, "notas": notas,
        "lider_id": str(interaction.user.id),
        "fecha": datetime.now().strftime("%d/%m/%Y %H:%M")
    }
    datos["solicitudes_pendientes"].append(solicitud)
    guardar_datos(datos)
    await interaction.response.send_message(
        embed=embed_base("⚔️ Raid registrada",
            f"**{cueva_display}** [{dificultad.upper()}] — {puntos} pts\n"
            f"Estado: **pendiente de validación**.\n{'📝 ' + notas if notas else ''}", 0xffa500),
        ephemeral=True)
    await notificar_log(interaction.guild,
        f"⚔️ Raid pendiente: **{nombre_tribu}** → {cueva_display} [{dificultad.upper()}] ({puntos} pts)")

@bot.tree.command(name="aprobar-raid", description="[ADMIN] Aprueba o rechaza una raid")
@app_commands.describe(id_solicitud="ID de la solicitud", accion="aprobar o rechazar")
@app_commands.choices(accion=[
    app_commands.Choice(name="Aprobar", value="aprobar"),
    app_commands.Choice(name="Rechazar", value="rechazar"),
])
async def aprobar_raid(interaction: discord.Interaction, id_solicitud: str, accion: str):
    if not es_admin(interaction):
        await interaction.response.send_message(
            embed=embed_base("❌ Sin permisos", "Solo los admins pueden usar este comando.", 0xff4444), ephemeral=True)
        return
    datos = cargar_datos()
    sol = next((s for s in datos["solicitudes_pendientes"]
                if s["id"] == id_solicitud and s["tipo"] == "raid"), None)
    if not sol:
        await interaction.response.send_message(
            embed=embed_base("❌ Error", f"No se encontró la raid `{id_solicitud}`.", 0xff4444), ephemeral=True)
        return
    datos["solicitudes_pendientes"].remove(sol)
    if accion == "aprobar":
        tribu = datos["tribus"].get(sol["tribu"])
        if not tribu:
            await interaction.response.send_message(
                embed=embed_base("❌ Error", "La tribu ya no existe.", 0xff4444), ephemeral=True)
            return
        tribu["puntos"] += sol["puntos"]
        tribu["raids"].append({
            "cueva": sol["cueva"], "dificultad": sol.get("dificultad", "normal"),
            "puntos": sol["puntos"], "fecha": sol["fecha"],
            "validado_por": interaction.user.display_name
        })
        guardar_datos(datos)
        await actualizar_embed_tribu(interaction.guild, sol["tribu"])
        await actualizar_marcador(interaction.guild)
        await interaction.response.send_message(
            embed=embed_base("✅ Raid aprobada",
                f"**{sol['tribu']}** en **{sol['cueva']}** +**{sol['puntos']} pts**", 0x00ff88))
        await notificar_log(interaction.guild,
            f"✅ Raid aprobada: **{sol['tribu']}** +{sol['puntos']} pts ({sol['cueva']})")
    else:
        guardar_datos(datos)
        await interaction.response.send_message(
            embed=embed_base("❌ Raid rechazada",
                f"Raid de **{sol['tribu']}** en **{sol['cueva']}** rechazada.", 0xff4444))

@bot.tree.command(name="marcador", description="[ADMIN] Publica/actualiza el marcador en el canal configurado")
async def marcador(interaction: discord.Interaction):
    if not es_admin(interaction):
        await interaction.response.send_message(
            embed=embed_base("❌ Sin permisos", "Solo los admins pueden publicar el marcador.", 0xff4444), ephemeral=True)
        return
    datos = cargar_datos()
    if not datos.get("marcador_channel"):
        await interaction.response.send_message(
            embed=embed_base("❌ Error", "Configura primero el canal con `/set-marcador-channel`.", 0xff4444), ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    await actualizar_marcador(interaction.guild)
    await interaction.followup.send(
        embed=embed_base("✅ Marcador publicado", "El ranking ha sido publicado/actualizado.", 0x00ff88), ephemeral=True)

@bot.tree.command(name="mi-marcador", description="Ver tu posición en el ranking (solo tú lo ves)")
async def mi_marcador(interaction: discord.Interaction):
    datos = cargar_datos()
    nombre_tribu = es_lider(interaction, datos)
    if not nombre_tribu and not es_admin(interaction):
        await interaction.response.send_message(
            embed=embed_base("❌ Error", "Solo los líderes de tribu pueden usar este comando.", 0xff4444), ephemeral=True)
        return
    sorted_tribus = sorted(datos["tribus"].items(), key=lambda x: x[1]["puntos"], reverse=True)
    medallas = ["🥇", "🥈", "🥉"]
    desc = ""
    for i, (nombre, t) in enumerate(sorted_tribus):
        medalla = medallas[i] if i < 3 else f"`#{i+1}`"
        if nombre == nombre_tribu:
            desc += f"**➤ {medalla} {t['tag']} {nombre} — {t['puntos']} pts ◄ TU TRIBU**\n"
        else:
            desc += f"{medalla} {t['tag']} {nombre} — {t['puntos']} pts\n"
    embed = embed_base("🏆 Alpha Cluster — Tu posición", desc or "Aún no hay tribus.", 0xffd700)
    embed.add_field(name="📅 Consultado", value=datetime.now().strftime("%d/%m/%Y %H:%M"), inline=True)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="tribu", description="Ver información pública de una tribu")
@app_commands.describe(nombre="Nombre de la tribu")
async def tribu_info(interaction: discord.Interaction, nombre: str):
    datos = cargar_datos()
    match = next((k for k in datos["tribus"] if nombre.lower() in k.lower()), None)
    if not match:
        await interaction.response.send_message(
            embed=embed_base("❌ Error", f"No se encontró la tribu **{nombre}**.", 0xff4444), ephemeral=True)
        return
    t = datos["tribus"][match]
    embed = build_embed_tribu(match, t)
    es_lider_tribu = str(interaction.user.id) == t["lider_id"]
    if es_admin(interaction) or es_lider_tribu:
        embed.add_field(name="🗺️ Cueva Base", value=t.get("nombre_cueva", "No especificada"), inline=True)
        embed.add_field(name="📍 Coordenadas", value=f"`{t.get('coordenadas', 'No especificadas')}`", inline=True)
    if t["raids"]:
        ultimas = t["raids"][-3:][::-1]
        raids_txt = "\n".join([f"• {r['cueva']} [{r.get('dificultad','normal').upper()}] (+{r['puntos']} pts) — {r['fecha']}" for r in ultimas])
        embed.add_field(name="🗡️ Últimas raids", value=raids_txt, inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="mis-tribus", description="Ver tu tribu con todos los datos")
async def mis_tribus(interaction: discord.Interaction):
    datos = cargar_datos()
    nombre_tribu = es_lider(interaction, datos)
    if not nombre_tribu:
        await interaction.response.send_message(
            embed=embed_base("ℹ️ Sin tribu", "No eres líder de ninguna tribu registrada.", 0x888888), ephemeral=True)
        return
    t = datos["tribus"][nombre_tribu]
    embed = build_embed_tribu(nombre_tribu, t)
    embed.add_field(name="🗺️ Cueva Base", value=t.get("nombre_cueva", "No especificada"), inline=True)
    embed.add_field(name="📍 Coordenadas", value=f"`{t.get('coordenadas', 'No especificadas')}`", inline=True)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="cuevas", description="Ver todas las cuevas de Fjordur y sus puntos")
async def cuevas(interaction: discord.Interaction):
    embed = embed_base("🗺️ Cuevas de Fjordur", color=0x7b2d8b)
    dificil_txt = "\n".join([f"🔴 **{n}** — Normal: `{p[0]}pts` | Hard: `{p[1]}pts`" for n, p in CUEVAS_DIFICIL.items()])
    media_txt = "\n".join([f"🟡 **{n}** — Normal: `{p[0]}pts` | Hard: `{p[1]}pts`" for n, p in CUEVAS_MEDIA.items()])
    facil_txt = "\n".join([f"🟢 **{n}** — Normal: `{p[0]}pts` | Hard: `{p[1]}pts`" for n, p in CUEVAS_FACIL.items()])
    embed.add_field(name="💀 Dificultad Alta", value=dificil_txt, inline=False)
    embed.add_field(name="⚠️ Dificultad Media", value=media_txt, inline=False)
    embed.add_field(name="✅ Dificultad Fácil", value=facil_txt, inline=False)
    embed.add_field(name="⚙️ Cuevas Variables", value="Puntos asignados por el admin.", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="añadir-miembro", description="Añade un miembro a tu tribu")
@app_commands.describe(psn_id="PSN ID del nuevo miembro", discord_id="ID de Discord del nuevo miembro")
async def añadir_miembro(interaction: discord.Interaction, psn_id: str, discord_id: str):
    datos = cargar_datos()
    nombre_tribu = es_lider(interaction, datos)
    if not nombre_tribu:
        await interaction.response.send_message(
            embed=embed_base("❌ Error", "Solo los líderes pueden añadir miembros.", 0xff4444), ephemeral=True)
        return
    tribu = datos["tribus"][nombre_tribu]
    if len(tribu["miembros_psn"]) >= 6:
        await interaction.response.send_message(
            embed=embed_base("❌ Error", "El máximo es 6 miembros por tribu.", 0xff4444), ephemeral=True)
        return
    if psn_id in tribu["miembros_psn"]:
        await interaction.response.send_message(
            embed=embed_base("❌ Error", f"**{psn_id}** ya es miembro de la tribu.", 0xff4444), ephemeral=True)
        return
    did_clean = discord_id.strip().strip("<@>").strip("!")
    nuevo_idx = str(len(tribu["miembros_psn"]))
    tribu["miembros_psn"].append(psn_id)
    tribu.setdefault("discord_ids", {})[nuevo_idx] = did_clean
    guardar_datos(datos)
    await actualizar_embed_tribu(interaction.guild, nombre_tribu)
    await interaction.response.send_message(
        embed=embed_base("✅ Miembro añadido",
            f"**{psn_id}** (<@{did_clean}>) añadido a **{nombre_tribu}**.", 0x00ff88), ephemeral=True)

@bot.tree.command(name="eliminar-miembro", description="Elimina un miembro de tu tribu")
@app_commands.describe(psn_id="PSN ID del miembro a eliminar")
async def eliminar_miembro(interaction: discord.Interaction, psn_id: str):
    datos = cargar_datos()
    nombre_tribu = es_lider(interaction, datos)
    if not nombre_tribu:
        await interaction.response.send_message(
            embed=embed_base("❌ Error", "Solo los líderes pueden eliminar miembros.", 0xff4444), ephemeral=True)
        return
    tribu = datos["tribus"][nombre_tribu]
    if psn_id not in tribu["miembros_psn"]:
        await interaction.response.send_message(
            embed=embed_base("❌ Error", f"**{psn_id}** no es miembro de la tribu.", 0xff4444), ephemeral=True)
        return
    idx = tribu["miembros_psn"].index(psn_id)
    tribu["miembros_psn"].remove(psn_id)
    discord_ids = tribu.get("discord_ids", {})
    discord_ids.pop(str(idx), None)
    nuevo_map = {str(ni): v for ni, (_, v) in enumerate(
        sorted({k: v for k, v in discord_ids.items()}.items(), key=lambda x: int(x[0])))}
    tribu["discord_ids"] = nuevo_map
    guardar_datos(datos)
    await actualizar_embed_tribu(interaction.guild, nombre_tribu)
    await interaction.response.send_message(
        embed=embed_base("✅ Miembro eliminado", f"**{psn_id}** eliminado de **{nombre_tribu}**.", 0xff4444), ephemeral=True)

@bot.tree.command(name="eliminar-tribu", description="[ADMIN] Elimina una tribu del servidor")
@app_commands.describe(nombre="Nombre de la tribu a eliminar")
async def eliminar_tribu(interaction: discord.Interaction, nombre: str):
    if not es_admin(interaction):
        await interaction.response.send_message(
            embed=embed_base("❌ Sin permisos", "Solo los admins pueden eliminar tribus.", 0xff4444), ephemeral=True)
        return
    datos = cargar_datos()
    match = next((k for k in datos["tribus"] if nombre.lower() in k.lower()), None)
    if not match:
        await interaction.response.send_message(
            embed=embed_base("❌ Error", f"No se encontró la tribu **{nombre}**.", 0xff4444), ephemeral=True)
        return
    msg_id = datos["tribus"][match].get("mensaje_id")
    ch_id = datos.get("tribus_channel")
    if msg_id and ch_id:
        try:
            ch = interaction.guild.get_channel(int(ch_id))
            msg = await ch.fetch_message(int(msg_id))
            await msg.delete()
        except:
            pass
    del datos["tribus"][match]
    guardar_datos(datos)
    await actualizar_marcador(interaction.guild)
    await interaction.response.send_message(
        embed=embed_base("🗑️ Tribu eliminada", f"La tribu **{match}** ha sido eliminada.", 0xff4444))

@bot.tree.command(name="listar-tribus", description="[ADMIN] Ver todas las tribus registradas con sus miembros")
async def listar_tribus(interaction: discord.Interaction):
    if not es_admin(interaction):
        await interaction.response.send_message(
            embed=embed_base("❌ Sin permisos", "Solo los admins pueden usar este comando.", 0xff4444), ephemeral=True)
        return
    datos = cargar_datos()
    if not datos["tribus"]:
        await interaction.response.send_message(
            embed=embed_base("🏕️ Tribus registradas", "No hay ninguna tribu registrada aún."), ephemeral=True)
        return
    sorted_tribus = sorted(datos["tribus"].items(), key=lambda x: x[1]["puntos"], reverse=True)
    total_miembros = sum(len(t["miembros_psn"]) for _, t in sorted_tribus)
    embeds = []
    embed = embed_base(f"🏕️ Tribus — {len(sorted_tribus)} tribus · {total_miembros} jugadores", color=0x00b4d8)
    for i, (nombre, t) in enumerate(sorted_tribus):
        discord_ids = t.get("discord_ids", {})
        miembros_txt = "\n".join([
            f"  🎮 `{t['miembros_psn'][int(k)]}` — <@{v}>" for k, v in discord_ids.items()
        ]) if discord_ids else "\n".join([f"  🎮 `{m}`" for m in t["miembros_psn"]])
        campo = (f"👑 <@{t['lider_id']}>\n"
                 f"🏆 **{t['puntos']} pts** · ⚔️ **{len(t['raids'])} raids**\n"
                 f"🗺️ {t.get('nombre_cueva','N/A')} | 📍 `{t.get('coordenadas','N/A')}`\n"
                 f"👥 ({len(t['miembros_psn'])}/6):\n{miembros_txt}\n"
                 f"📅 {t['fecha_registro']}")
        embed.add_field(
            name=f"{'🥇' if i==0 else '🥈' if i==1 else '🥉' if i==2 else '▫️'} {t['tag']} {nombre}",
            value=campo, inline=False)
        if (i + 1) % 10 == 0:
            embeds.append(embed)
            embed = embed_base("🏕️ Tribus (cont.)", color=0x00b4d8)
    embeds.append(embed)
    await interaction.response.send_message(embed=embeds[0], ephemeral=True)
    for extra in embeds[1:]:
        await interaction.followup.send(embed=extra, ephemeral=True)

@bot.tree.command(name="set-log-channel", description="[ADMIN] Canal de logs del bot")
@app_commands.describe(canal="Canal de logs")
async def set_log_channel(interaction: discord.Interaction, canal: discord.TextChannel):
    if not es_admin(interaction):
        await interaction.response.send_message(
            embed=embed_base("❌ Sin permisos", "Solo los admins pueden configurar esto.", 0xff4444), ephemeral=True)
        return
    datos = cargar_datos()
    datos["log_channel"] = str(canal.id)
    guardar_datos(datos)
    await interaction.response.send_message(
        embed=embed_base("✅ Configurado", f"Logs → {canal.mention}", 0x00ff88), ephemeral=True)

@bot.tree.command(name="set-tribus-channel", description="[ADMIN] Canal donde se publicarán las fichas de tribus aprobadas")
@app_commands.describe(canal="Canal de fichas de tribus")
async def set_tribus_channel(interaction: discord.Interaction, canal: discord.TextChannel):
    if not es_admin(interaction):
        await interaction.response.send_message(
            embed=embed_base("❌ Sin permisos", "Solo los admins pueden configurar esto.", 0xff4444), ephemeral=True)
        return
    datos = cargar_datos()
    datos["tribus_channel"] = str(canal.id)
    guardar_datos(datos)
    await interaction.response.send_message(
        embed=embed_base("✅ Configurado", f"Fichas de tribus → {canal.mention}", 0x00ff88), ephemeral=True)

@bot.tree.command(name="set-marcador-channel", description="[ADMIN] Canal donde se publicará el ranking público")
@app_commands.describe(canal="Canal del marcador")
async def set_marcador_channel(interaction: discord.Interaction, canal: discord.TextChannel):
    if not es_admin(interaction):
        await interaction.response.send_message(
            embed=embed_base("❌ Sin permisos", "Solo los admins pueden configurar esto.", 0xff4444), ephemeral=True)
        return
    datos = cargar_datos()
    datos["marcador_channel"] = str(canal.id)
    datos["marcador_message_id"] = None
    guardar_datos(datos)
    await interaction.response.send_message(
        embed=embed_base("✅ Configurado", f"Marcador → {canal.mention}", 0x00ff88), ephemeral=True)

@bot.tree.command(name="ayuda", description="Ver todos los comandos disponibles")
async def ayuda(interaction: discord.Interaction):
    embed = embed_base("📖 Comandos del Bot ARK Fjordur", color=0x00b4d8)
    embed.add_field(name="🏕️ Tribus", value=
        "`/registrar-tribu` — Registra tu tribu (requiere aprobación)\n"
        "`/mis-tribus` — Ver tu tribu con cueva y coords\n"
        "`/tribu [nombre]` — Info pública de una tribu\n"
        "`/añadir-miembro` — Añade miembro PSN + Discord\n"
        "`/eliminar-miembro` — Elimina un miembro de tu tribu", inline=False)
    embed.add_field(name="⚔️ Raids", value=
        "`/añadir-raid` — Registrar una raid (requiere aprobación)\n"
        "`/cuevas` — Ver cuevas de Fjordur y sus puntos", inline=False)
    embed.add_field(name="🏆 Ranking", value=
        "`/mi-marcador` — Ver el ranking (solo tú lo ves)", inline=False)
    embed.add_field(name="🔐 Admin", value=
        "`/marcador` — Publicar/actualizar el ranking público\n"
        "`/solicitudes-pendientes` — Ver solicitudes pendientes\n"
        "`/aprobar-tribu [id] [acción]` — Aprobar/rechazar tribu\n"
        "`/aprobar-raid [id] [acción]` — Aprobar/rechazar raid\n"
        "`/listar-tribus` — Ver todas las tribus con detalle\n"
        "`/eliminar-tribu [nombre]` — Eliminar una tribu\n"
        "`/set-log-channel` — Canal de logs\n"
        "`/set-tribus-channel` — Canal de fichas de tribus\n"
        "`/set-marcador-channel` — Canal del ranking público", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} comandos slash sincronizados")
    except Exception as e:
        print(f"❌ Error sincronizando comandos: {e}")
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name="ARK Fjordur PS4 🦕"))

if __name__ == "__main__":
    bot.run(TOKEN)
