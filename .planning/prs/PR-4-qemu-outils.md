# PR 4 — mpu_spells/outils.py: let ML_PLATFORM_DIR override the hardcoded platform path

- **Target repo:** `reticulatedpines/qemu-eos`
- **Target branch:** `qemu-eos-v4.2.1` (based on `4b667a1d3c`, the local clone's HEAD)
- **Source branch:** none yet, by design — no branch was created inside the shared
  `qemu-eos/` clone (another session has live uncommitted work there). Chris
  creates it from the patch file when posting; commands below.
- **Files:** `hw/eos/mpu_spells/outils.py` (1 line)
- **Final patch file:** `.planning/prs/PR-4-qemu-outils-ML_PLATFORM_DIR.patch`
  (identical to `patches/0003-qemu-eos-outils-ML_PLATFORM_DIR.patch`; verified
  still an exact match for what is applied in the working `qemu-eos/` clone)

## Title

```
mpu_spells: let ML_PLATFORM_DIR override the hardcoded magic-lantern platform path
```

## PR body (ready to paste)

```markdown
`extract_init_spells.py` dies on startup for anyone not using the pre-2020
repository layout: `outils.py:get_switch_names()` hardcodes

    ml_dir = "../../../../../magic-lantern/platform/"

and `os.listdir(ml_dir)` raises `FileNotFoundError` when the sibling checkout
is `magiclantern_simplified` (or anywhere else). This makes the whole
spell-extraction pipeline unusable with current ML checkouts unless the user
recreates the old directory structure by hand.

One-line fix: honour an `ML_PLATFORM_DIR` environment variable, keeping the
old path as the default.

    ml_dir = os.environ.get("ML_PLATFORM_DIR", "../../../../../magic-lantern/platform/")

Usage:

    ML_PLATFORM_DIR=/path/to/magiclantern_simplified/platform/ \
        python3 extract_init_spells.py 6D2-startup.log > 6D2.h

### Test evidence

Used in anger for a 6D2 MPU spell capture: with the override pointing at a
`magiclantern_simplified/platform/` checkout, `extract_init_spells.py`
processed a 1310-line 6D2 startup log and generated a 23-spell `6D2.h`
(button-name resolution via the platform's `gui.h` included). Without the
override, the script dies in `os.listdir`.

### Risk analysis

None worth the name: when `ML_PLATFORM_DIR` is unset the behavior is
byte-identical to today. `os` was already imported in `outils.py`.
```

## Exact commands for Chris (branch + push)

```sh
cd "/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/qemu-eos"

# The working tree has uncommitted work (patch 0003 itself, another session's
# cam_config files). Branch from the clean commit without touching the tree:
git stash push -- hw/eos/mpu_spells/outils.py          # temporarily park the applied patch
git checkout -b outils-ml-platform-dir 4b667a1d3c
git apply "/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/.planning/prs/PR-4-qemu-outils-ML_PLATFORM_DIR.patch"
git add hw/eos/mpu_spells/outils.py
git commit -m "mpu_spells: let ML_PLATFORM_DIR override the hardcoded magic-lantern platform path

outils.py:get_switch_names() hardcodes ../../../../../magic-lantern/platform/
(the pre-2020 repo layout), so extract_init_spells.py dies in os.listdir()
for anyone with a magiclantern_simplified checkout. Honour an ML_PLATFORM_DIR
environment variable instead, keeping the old path as the default.

Tested: with ML_PLATFORM_DIR pointing at a magiclantern_simplified/platform/
checkout, extract_init_spells.py processed a 1310-line 6D2 startup log and
generated a 23-spell 6D2.h. Behavior is unchanged when the variable is unset."

# back to the working branch and restore the parked state:
git checkout qemu-eos-v4.2.1
git stash pop

# one-time: add your fork (create it on GitHub first)
git remote add fork git@github.com:<YOUR_GITHUB_USER>/qemu-eos.git
git push fork outils-ml-platform-dir

gh pr create --repo reticulatedpines/qemu-eos \
  --base qemu-eos-v4.2.1 --head <YOUR_GITHUB_USER>:outils-ml-platform-dir \
  --title "mpu_spells: let ML_PLATFORM_DIR override the hardcoded magic-lantern platform path" \
  --body-file <(sed -n '/^```markdown$/,/^```$/p' \
      "/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/.planning/prs/PR-4-qemu-outils.md" \
      | sed '1d;$d')
```

Caution: run the `git stash push`/`pop` pair only when no other session is
mid-task in `qemu-eos/` — the same shared-tree hazard as everywhere else in
this project.
