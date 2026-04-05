# 🦕 ARK Bot — Fjordur PS4

Bot de Discord para gestión de tribus y ranking Alpha Cluster en ARK Survival Evolved PS4.

---

## ⚙️ Instalación en Railway (gratis)

### 1. Crear el Bot en Discord
1. Ve a https://discord.com/developers/applications
2. Haz clic en **New Application** → ponle nombre (ej: "ARK Fjordur Bot")
3. Ve a **Bot** → **Add Bot**
4. En **Privileged Gateway Intents**, activa:
   - ✅ SERVER MEMBERS INTENT
   - ✅ MESSAGE CONTENT INTENT
5. Copia el **TOKEN** (lo necesitarás luego)
6. Ve a **OAuth2 → URL Generator**:
   - Scopes: `bot` + `applications.commands`
   - Bot Permissions: `Send Messages`, `Embed Links`, `Read Message History`, `Use Slash Commands`
7. Copia la URL generada y ábrela para invitar el bot a tu servidor

### 2. Subir a Railway
1. Ve a https://railway.app y crea una cuenta (gratis)
2. Haz clic en **New Project → Deploy from GitHub repo**
   - Si no tienes el código en GitHub, usa **Empty Project → Add Service → GitHub Repo**
   - Sube los archivos `bot.py`, `requirements.txt` y `Procfile` a un repo de GitHub
3. En Railway, ve a tu proyecto → **Variables** y añade:
   ```
   DISCORD_TOKEN = TU_TOKEN_AQUI
   ```
4. Railway detectará el `Procfile` y arrancará el bot automáticamente

### 3. Archivos necesarios en tu repo GitHub
```
ark_bot/
├── bot.py           ← el bot principal
├── requirements.txt ← dependencias
└── Procfile         ← comando de inicio para Railway
```

---

## 📋 Comandos disponibles

### 🏕️ Líderes de tribu
| Comando | Descripción |
|---|---|
| `/registrar-tribu` | Registra tu tribu (pendiente de aprobación) |
| `/mis-tribus` | Ver tu tribu y sus datos |
| `/añadir-raid` | Registrar una raid completada |
| `/añadir-miembro` | Añadir miembro PSN a tu tribu |

### 🌍 Todos los miembros
| Comando | Descripción |
|---|---|
| `/marcador` | Ver ranking Alpha Cluster |
| `/tribu [nombre]` | Info detallada de una tribu |
| `/cuevas` | Lista de cuevas y puntos |
| `/ayuda` | Ver todos los comandos |

### 🔐 Solo Admins
| Comando | Descripción |
|---|---|
| `/solicitudes-pendientes` | Ver solicitudes de tribu y raid |
| `/aprobar-tribu [id] aprobar/rechazar` | Validar registro de tribu |
| `/aprobar-raid [id] aprobar/rechazar` | Validar raid |
| `/eliminar-tribu [nombre]` | Eliminar una tribu |
| `/set-log-channel [canal]` | Configurar canal de logs |

---

## 🗺️ Cuevas de Fjordur y puntos fijos

| Cueva | Puntos |
|---|---|
| Cueva del Hielo (Fácil) | 5 |
| Cueva del Hielo (Media) | 10 |
| Cueva del Hielo (Difícil) | 20 |
| Cueva Acuática | 15 |
| Cueva de Lava | 25 |
| Cueva Asgard | 30 |
| Cueva Jotunheim | 35 |
| Cueva Vanaheim | 30 |
| Cueva del Jefe (Beyla) | 50 |
| Cueva del Jefe (Steinbjörn) | 60 |
| Cueva del Jefe (Skoll & Hati) | 70 |

Las cuevas variables las puntúa el admin según dificultad.

---

## 💡 Flujo de uso

```
Líder: /registrar-tribu → Admin ve en /solicitudes-pendientes → Admin aprueba con /aprobar-tribu
Líder: /añadir-raid     → Admin ve en /solicitudes-pendientes → Admin aprueba con /aprobar-raid
Todos:  /marcador        → Ven el ranking actualizado en tiempo real
```

---

## 📝 Notas
- Los datos se guardan en `data.json` en el mismo directorio
- En Railway, los datos persisten entre reinicios gracias al volumen
- El bot detecta admins por permisos de administrador O por roles llamados: admin, administrador, moderador, mod
