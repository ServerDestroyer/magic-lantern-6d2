# DM to send to the ML admin(s)

Copy-paste this into a DM to the Magic Lantern Discord server admins.

---

Hey! I'm working on the 6D2 port and would like to keep a local, offline
index of the dev channels so I can search past discussion while developing.

Would it be OK to invite a read-only logging bot? A few details so you can
judge it:

- **Permissions**: View Channels + Read Message History only (permission
  integer 66560). No Send Messages, no Manage anything — the invite literally
  can't grant more than that.
- **Code**: ~80 lines, no send calls anywhere, happy to paste the whole thing
  here or link it.
- **What it does**: reads messages, writes them to local markdown files on my
  machine. Never posts, reacts, or DMs anyone.

Invite link (you can inspect the requested permissions before accepting):
https://discord.com/oauth2/authorize?client_id=1538248909204226158&permissions=66560&integration_type=0&scope=bot

Totally understand if the answer's no — just figured I'd ask since it'd save
me a lot of scrolling through old threads.
