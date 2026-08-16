# Canon EOS 6D Mark II — Real Controls, Menus, and ML Operation

Reference for writing camera instructions that match **this** body. Every Canon name below is
taken from the official *EOS 6D Mark II Instruction Manual* (Nomenclature, pp. 28–37; page
references in parentheses are that manual's page numbers). Every Magic Lantern claim is taken
from the 6D2 port source in this repo, not from generic ML docs.

Sources: Canon EOS 6D Mark II Instruction Manual (610 pp., via ManualsLib), and
`ml/platform/6D2.111/gui.h`, `ml/platform/6D2.111/internals.h`, `ml/platform/6D2.111/consts.h`,
`ml/src/menu.c`, `ml/src/gui-common.c`.

---

## 1. Control map — Canon's real names

### Top plate (manual p.28)

| Canon's name | Notes |
|---|---|
| **Mode Dial** (p.35, 57) | Turn while holding the **Mode Dial lock-release button** in its center. Positions: A+ / CA / SCN / Bulb / **M** / Av / Tv / P / C1 / C2. **There is no movie position on the Mode Dial.** |
| **Main Dial** (p.57) | The knurled wheel behind the shutter button. |
| Shutter button | Half-press = metering/AF. |
| **Drive mode selection button** | Top-left cluster. |
| **ISO speed setting button** | Top-left cluster. |
| **Metering mode selection button** | Top-left cluster. |
| **LCD panel illumination button** (p.60) | The top-panel backlight button. ML maps this as `BGMT_LIGHT`. |
| **AF operation / AF method selection button** | Top-left cluster. |
| **AF area selection button** | Top-left cluster. |
| LCD panel | Monochrome top display. |

### Back (manual pp.29–30)

| Canon's name | Notes |
|---|---|
| **Live View shooting / Movie shooting switch** (p.289/325) | The collar/lever that **rings the START/STOP button**. Two positions: still-camera icon (Live View shooting) and movie-camera icon `<k>` (Movie shooting). **This is the only way into movie mode.** |
| **Start/Stop button** (p.290, 326) | Sits inside that switch. Starts Live View, or starts/stops movie recording. |
| **Menu button** (p.64) | Top-left of the LCD monitor. |
| **Info button** (p.60, 80, 293, 334, 388) | Next to MENU. |
| **AF start button** — printed **AF-ON** (p.56, 130, 292, 337) | Back-button AF. |
| **AE lock / FE lock button** (p.249, 278) | The `*` button. |
| **AF point selection button** (p.136, 137) | The right-hand magnifier-with-dots button next to `*`. |
| **Quick Control button** — printed **Q** (p.61) | Opens Canon's Quick Control screen. |
| **Setting button** — printed **SET** (p.64) | Center of the Quick Control Dial. |
| **Quick Control Dial** (p.58) | The large rear thumbwheel. |
| **Multi-controller** (p.59) | **The 6D2 does have one.** Canon: "The `<9>` consists of an eight-direction key." It is an eight-way nub, **not** a 5D Mark IV-style joystick, and it has **no center-press event** exposed to ML. |
| **Multi function lock switch** (p.59, 88) | Marked **LOCK**, under the Quick Control Dial. **Up = lock engaged, down = lock released.** By default it locks the Quick Control Dial; `[54: Multi function lock]` chooses which controls it locks. When engaged, `LOCK` appears on the LV/movie screen and `L` on the LCD panel. |
| **Playback button** (p.388) | Blue triangle. |
| **Erase button** (p.430) | The trash-can button, bottom-left of the back. **This is the ML menu key.** |
| **Index / Magnify / Reduce button** (p.399/317, 321, 404) | Single magnify button; zoom level is then driven by the Main Dial. |
| **LCD monitor** (p.46, 64, 290, 326, 404) | **Fully articulating (vari-angle) capacitive touchscreen.** Canon documents touch operation throughout (pp.67, 319, 406). |
| Power switch, Speaker, Card slot / Access lamp | Single SD/SDHC/SDXC slot, UHS-I (not UHS-II). |

**Terminology traps to avoid:** there is no "movie position on the mode dial", no "top switch",
no "joystick", no "directional pad", no "control wheel", no "delete button" (Canon says *Erase
button*), no "OK button" (Canon says *SET*), and the Main Dial and Quick Control Dial are
different wheels — never just say "the dial".

---

## 2. Entering movie mode

1. Find the **Live View shooting / Movie shooting switch** — the collar around the **START/STOP**
   button at the top right of the back panel.
2. Turn it to the **movie-camera icon** `<k>` (manual p.325: "Movie shooting is enabled by setting
   the Live View shooting/Movie shooting switch to `<k>`").
3. The mirror flips up and the Live View image appears on the LCD monitor. The camera is now in
   movie mode even before recording.
4. Press **START/STOP** to begin recording; a red `●` appears top-right. Press **START/STOP**
   again to stop.

Setting the switch to `<k>` also changes the menu structure: a movie-only `[z4]` tab appears
(`[z2]` in Basic Zone modes) — manual p.373.

ML's source agrees: `internals.h` carries
`#define CONFIG_NO_DEDICATED_MOVIE_MODE` with the comment "Does the mode *dial* have movie mode?
6D2 does not, even though it does have a dedicated switch for movie." In `gui.h`,
`BGMT_REC` and `BGMT_LV` are the **same code `0x1e`** because it is the same physical button.

---

## 3. Manual-exposure movie (M mode)

1. Set the **Live View shooting / Movie shooting switch** to `<k>` (movie) **first**.
2. Set the **Mode Dial** to **M** (Canon's `<a>`, "Manual exposure") — hold the Mode Dial
   lock-release button in the dial's center while turning.
3. Set shutter speed with the **Main Dial**, aperture with the **Quick Control Dial**, ISO with
   the **ISO speed setting button** + Main Dial.
4. If a dial refuses to move, the **LOCK** switch is up — push the **Multi function lock switch
   down** and try again (manual p.332 says this explicitly).

Shutter-speed range in movie M mode is frame-rate dependent (manual p.333):
59.94/50.00 fps → 1/4000–1/60 and 1/4000–1/50; 29.97/25.00 fps → 1/4000–1/30 and 1/4000–1/25.

The mode dial position `A+`, `CA`, `P`, `Tv`, `Av`, `Bulb` all give **autoexposure** movie; only
`M` gives manual (manual p.326).

---

## 4. Movie resolution / frame rate, and the PAL/NTSC gate

### Set the recording size

`MENU` → **`[z1]` (red Shooting tab 1, visible only while the LV/Movie switch is on `<k>`)** →
**`Movie rec. size`** → SET.

Choices are image size × frame rate × compression:

- Image size: **`1920x1080` (Full HD)** or **`1280x720` (HD)**. No VGA, no 4K (4K exists only for
  time-lapse movies, `[z1] Time-lapse movie`).
- Compression: **IPB (Standard)** or **IPB (Light)**. Container is **MP4**.
- Frame rate: **the list shown depends on the Video system setting.**

### The Video system gate (manual pp.341–342, 541)

`MENU` → **`[53]` Set-up 3 (yellow)** → **`Video system`** → **`For NTSC`** or **`For PAL`**.

| Video system | Frame rates offered |
|---|---|
| **For NTSC** | 59.94 fps, 29.97 fps, **and 23.98 fps** |
| **For PAL** | 50.00 fps, 25.00 fps (23.98 fps is *not* selectable) |

Canon: "The frame rate displayed on the `[z1: Movie rec. size]` screen switches automatically
depending on the `[53: Video system]` setting", and "If you change the `[53: Video system]`
setting, also set `[z1: Movie rec. size]` again."

**So: to get 25p you must first switch Video system to `For PAL`, then re-open `Movie rec. size`.
To get 59.94p or 23.98p you must be on `For NTSC`.** Changing Video system silently resets the
rec-size selection, so always re-verify the rec size afterwards.

Note `[53]` is not shown while Live View / movie shooting is active in some sub-cases; if the
Set-up 3 tab looks wrong, exit Live View (switch back to the still icon), change Video system,
then return to `<k>`.

---

## 5. Magic Lantern on the 6D2 — verified from source

All from `ml/platform/6D2.111/gui.h` unless noted.

### Opening the ML menu

**Press the Erase (trash-can) button.** In `ml/src/menu.c`:

```c
if (event->param == BGMT_TRASH || ... ) {
    if (gui_state == GUISTATE_IDLE || (gui_menu_shown() && !beta_should_warn()))
        give_semaphore( gui_sem );
```

and `gui.h` has `#define BGMT_TRASH 0xd`. The 6D2 defines **none** of
`CONFIG_LONG_PRESS_SET_MENU`, `CONFIG_LONG_PRESS_JOYSTICK_MENU`, `CONFIG_850D`, or `CONFIG_EOSM`,
so there is **no long-press variant** — a plain short press of **Erase** toggles the ML menu.

Constraint: the camera must be in an idle GUI state (`GUISTATE_IDLE`) — i.e. not inside the Canon
menu and not in playback. `consts.h` sets `GUIMODE_ML_MENU (lv ? 0x4E : GUIMODE_PLAY)`, so
outside Live View the ML menu piggybacks on playback GUI mode.

**Touch does not open the ML menu on this body.** Even though `gui.h` lists touch codes
(`BGMT_TOUCH_1_FINGER 0x69`, `BGMT_TOUCH_2_FINGER 0x71`, …), `CONFIG_TOUCHSCREEN` is **not**
defined in `platform/6D2.111/internals.h` — it is only defined for 100D, 650D, 700D, 70D and
EOS M. The two-finger-tap shortcut therefore does nothing on the 6D2 build. Instruct by button,
never by touch.

### Navigating the ML menu

| Action | Control on the 6D2 | ML code |
|---|---|---|
| Open / close ML menu | **Erase** button | `BGMT_TRASH 0xd` |
| Close ML menu (also) | **MENU** button; or half-press the shutter | `BGMT_MENU 0x6` |
| Move between menu **tabs** | **Main Dial** (top dial) | `BGMT_WHEEL_LEFT 0x2` / `BGMT_WHEEL_RIGHT 0x3` |
| Move between **items** in a tab | **Quick Control Dial** (rear dial) | `BGMT_WHEEL_UP 0x0` / `BGMT_WHEEL_DOWN 0x1` |
| Move up/down/left/right (same as the dials) | **Multi-controller**, 8-way | `BGMT_PRESS_UP 0x2f` … `BGMT_UNPRESS_UDLR 0x2e`; diagonals are ignored by `menu.c` |
| Select / toggle / enter edit | **SET** | `BGMT_PRESS_SET 0x4` |
| Open submenu / "Q action" | **Q** button | `BGMT_Q 0x1d` |
| Open submenu (also) | **Playback** button | `BGMT_PLAY 0xb` — `menu.c` folds `BGMT_PLAY` into the same case as `BGMT_Q` |
| Toggle the help / info page | **INFO** button | `BGMT_INFO 0x7` |
| Toggle LiveView-transparent mode (in LV) | **Magnify** button, or START/STOP | `BGMT_PRESS_ZOOM_IN 0x12`, `BGMT_LV 0x1e` |
| Zebras while in Canon playback | **LCD panel illumination** button | `BTN_ZEBRAS_FOR_PLAYBACK = BGMT_LIGHT 0x20` |
| Dismiss ML menu and shoot | half-press shutter | `BGMT_PRESS_HALFSHUTTER 0x47` (source comment flags this code as also firing for DOF preview / AE lock / AF-ON — treat half-shutter reports as approximate) |

Caveats recorded in the port source:

- There is **no zoom-out event** (`BGMT_PRESS_ZOOM_OUT` is commented out) — the Magnify button
  only opens zoom; the Main Dial changes the level.
- The **LOCK switch** codes (`0x77`/`0x78`) are commented out, so ML does not currently see the
  Multi function lock switch. If a dial appears dead in the ML menu, check the physical LOCK
  switch is **down**.
- The **LCD panel illumination** button emits no code outside menu mode.
- Digic 7: `CONFIG_NO_BFNT` — the bitmap font is loaded from the card, so ML text requires the
  ML files present on the card.

---

## 6. 6D2 quirks that matter to our tests

- **29 min 59 sec hard limit** (manual p.345). One clip stops automatically at 29:59; press
  START/STOP again to begin a new file. The on-screen counter shown before recording is the
  *remaining* time and will read `29:59` at the start of a clip.
- **4 GB behaviour depends on the filesystem** (manual p.345):
  - camera-formatted **SD/SDHC → FAT32**: past 4 GB the camera silently opens a *new* file; the
    clip plays back as separate files, not consecutively.
  - camera-formatted **SDXC → exFAT**: a >4 GB clip is stored as **one file**.
  For raw/mlv_lite testing prefer an SDXC card formatted **in the camera** so files are not split.
  Also note files >4 GB will not copy via plain OS file download — use a card reader (p.599).
- **Format in-camera before movie tests** (`MENU` → `[51]` → `Format card`; hold **Erase** on the
  format screen to add the *Low level format* checkmark — p.70).
- **Movie Servo AF defaults to Enable** (`[z4] Movie Servo AF`, p.373). It refocuses continuously
  without any button press, which moves exposure/focus mid-take and records lens noise. **Set it
  to `Disable` before any timing or raw-recording test**, or focus drift will be blamed on ML.
- **Card speed**: UHS-I only (not UHS-II). Canon's own minimum for Full HD IPB (Standard) is SD
  Speed Class 10; 4K time-lapse wants UHS-I Speed Class 3 / 90 MB/s.
- **Overheating** can stop movie recording before the nominal card-capacity time (p.382).
- **Movies are MP4**, not MOV, on this body — affects any file-extension assumptions in scripts.
- **Video system change resets Movie rec. size** — always re-verify frame rate after a PAL/NTSC
  switch.
- **Still photos cannot be taken during movie shooting** (p.333).

---

## 7. Instruction phrasebook

Use the left column. Never the right.

| Say this | Not this |
|---|---|
| "Flip the **Live View shooting / Movie shooting switch** — the collar around the START/STOP button on the back — to the **movie-camera icon**." | "Turn the top switch to the movie-camera icon" / "set the mode dial to movie" |
| "Press **START/STOP** to begin recording." | "Press the record button" / "press the shutter" |
| "Hold the **Mode Dial lock-release button** in the center of the dial and turn the **Mode Dial** to **M**." | "Turn the dial to manual" |
| "Turn the **Main Dial** (the wheel behind the shutter button)." | "Turn the top wheel" / "the front dial" |
| "Turn the **Quick Control Dial** (the big wheel on the back)." | "Turn the control wheel" / "the scroll wheel" |
| "Press **SET** (the button in the center of the Quick Control Dial)." | "Press OK" / "press enter" |
| "Press the **Q** button." | "Press the quick menu" / "the function button" |
| "Press the **Erase** button (the trash-can icon, bottom-left of the back) to open the Magic Lantern menu." | "Press delete" / "long-press trash" / "two-finger tap the screen" |
| "Push the **Multi function lock switch** (marked LOCK, under the Quick Control Dial) **down** to release the lock." | "Unlock the camera" / "flip the lock switch" (direction matters) |
| "Nudge the **Multi-controller** (the eight-way nub) up/down/left/right." | "Use the joystick" / "the D-pad" / "the arrow keys" |
| "Press the **AF-ON** button." | "Press back-button focus" |
| "Press **MENU**, go to the red **`[z1]`** tab, choose **Movie rec. size**." | "Go to the movie menu" |
| "Press **MENU**, go to the yellow **`[53]` Set-up 3** tab, choose **Video system**, set **For PAL**." | "Switch the camera to PAL" |
| "The **LCD monitor** is a vari-angle touchscreen — you can flip it out, but the ML menu does **not** respond to touch on this build; use the buttons." | "Tap the ML menu item" |

### Canonical sequence for a manual 1080p test clip

1. Set the **Live View shooting / Movie shooting switch** to the **movie-camera icon**.
2. Set the **Mode Dial** to **M** (hold the lock-release button in its center).
3. Push the **Multi function lock switch** (LOCK) **down**.
4. Press **MENU** → red **`[z1]`** tab → **Movie rec. size** → pick `1920x1080` + the frame rate
   → **SET**. (If the frame rate you want is missing: **MENU** → yellow **`[53]`** → **Video
   system** → `For NTSC` / `For PAL`, then come back and set Movie rec. size again.)
5. Press **MENU** → **`[z4]`** tab → **Movie Servo AF** → **Disable** → **SET**.
6. Press **MENU** to exit back to the Live View image.
7. Press the **Erase** button to open the Magic Lantern menu; **Main Dial** changes tab,
   **Quick Control Dial** changes item, **SET** toggles, **Q** opens the submenu, **INFO** shows
   help, **Erase** or **MENU** closes it.
8. Press **START/STOP** to record; press it again to stop (or it stops itself at 29:59).
