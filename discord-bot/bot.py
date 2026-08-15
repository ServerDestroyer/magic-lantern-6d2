#!/usr/bin/env python3
"""Read-only Discord logger for Magic Lantern dev channels.

Reads messages, writes them to local markdown files. Never posts, reacts,
or sends anything — the bot has no send permission in its invite, and this
code contains no send calls.

Run:  DISCORD_TOKEN=... python3 bot.py
Logs: logs/<server>/<channel>/YYYY-MM-DD.md
"""

import os
import re
import sys
from pathlib import Path

import discord

LOG_ROOT = Path(__file__).parent / "logs"
# How far back to backfill history per channel on startup (None = everything)
BACKFILL_LIMIT = 5000


def slug(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "-", name).strip("-") or "unnamed"


def write_msg(msg: discord.Message) -> None:
    d = LOG_ROOT / slug(msg.guild.name) / slug(msg.channel.name)
    d.mkdir(parents=True, exist_ok=True)
    f = d / (msg.created_at.strftime("%Y-%m-%d") + ".md")
    ts = msg.created_at.strftime("%H:%M")
    body = msg.content or ""
    for a in msg.attachments:
        body += f"\n[attachment: {a.filename} {a.url}]"
    with f.open("a", encoding="utf-8") as fh:
        fh.write(f"**{msg.author.display_name}** ({ts}): {body}\n\n")


intents = discord.Intents.default()
intents.message_content = True  # enable "Message Content Intent" in dev portal
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f"logged in as {client.user}; backfilling history...")
    for guild in client.guilds:
        for ch in guild.text_channels:
            perms = ch.permissions_for(guild.me)
            if not (perms.view_channel and perms.read_message_history):
                continue
            try:
                async for msg in ch.history(limit=BACKFILL_LIMIT, oldest_first=True):
                    write_msg(msg)
                print(f"  backfilled #{ch.name}")
            except discord.Forbidden:
                pass
    print("backfill done; now logging live messages.")


@client.event
async def on_message(msg: discord.Message):
    if msg.guild is not None:
        write_msg(msg)


if __name__ == "__main__":
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        sys.exit("set DISCORD_TOKEN environment variable (bot token, dev portal)")
    client.run(token)
