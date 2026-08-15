# ML Dev Read-Only Logger Bot

Logs Discord dev-channel messages to local markdown files so Claude can index
and answer "where is 6D2 development?" questions. It cannot post: the invite
grants no send permission and the code contains no send calls.

## One-time setup

1. Go to https://discord.com/developers/applications → **New Application**
   (name it e.g. `ml-devlog-readonly`).
2. Left sidebar → **Bot**:
   - Under *Privileged Gateway Intents*, enable **Message Content Intent**.
   - Click **Reset Token**, copy it. Keep it secret.
3. Left sidebar → **OAuth2 → URL Generator**:
   - Scopes: `bot`
   - Bot Permissions: **View Channels** + **Read Message History** only.
   - Copy the generated URL — this is the invite link you give the ML admins.
     (Permission integer is `66560`; they can verify it grants nothing else.)

## Run

```sh
cd discord-bot
DISCORD_TOKEN=your-token nix-shell -p python3Packages.discordpy --run "python3 bot.py"
```

On startup it backfills up to 5000 messages per readable channel, then logs
live messages. Output: `logs/<server>/<channel>/YYYY-MM-DD.md`.

## What to tell the ML admins

> I'm working on the 6D2 port and would like to keep a local, offline index of
> the dev channels so I can search past discussion while developing. May I
> invite a read-only bot? Invite link grants View Channels + Read Message
> History only — no send permission. Code is ~80 lines, happy to share:
> [link/paste bot.py]
