# PR 2 — property: don't wait out the timeout on writes denied by the whitelist (D678)

- **Target repo:** `reticulatedpines/magiclantern_simplified`
- **Target branch:** `dev` (based on `dev` @ `3f24042a4`, current local `origin/dev`)
- **Source branch:** `d678-prop-wait-denied` (1 commit: `7454309f7`)
- **Files:** `src/property.c` (+8)
- **Local branch location:** the `magiclantern_simplified` clone in this project (note: `magiclantern_simplified` is a symlink to `ml/`); worktree with the built tree at `/home/chris/ml6d2/trackC-wt2`
- **Patch file (durability copy):** `.planning/prs/0001-property-don-t-wait-out-the-timeout-on-write.branch2.patch`

## Title

```
property: don't wait out the timeout on writes denied by the whitelist (D678)
```

## PR body (ready to paste)

```markdown
On DIGIC 678X ports, `prop_request_change()` silently drops any write to a
property that is not in the port's `prop_write_allow[]` whitelist (the `return`
in the `else` branch at the `is_prop_allowed()` check). But
`prop_request_change_wait()` still polls for the ack afterwards — an ack that
can never arrive, because no write was ever issued — so every denied write
burns the full timeout.

### The livelock chain this causes (observed on 6D2)

1. `gui_uilock()` calls `prop_request_change_wait(PROP_ICU_UILOCK, ..., 2000)`.
2. `PROP_ICU_UILOCK` is whitelisted on **no** DIGIC 7 port, so the write is
   silently dropped and the wait burns the full 2000 ms.
3. `mlv_lite` wraps each buffer reallocation in a `gui_uilock()` pair from its
   polling loop, so every reallocation costs ~2 s per uilock call, back to
   back — raw video startup degrades into a chain of 2 s stalls that looks
   like a frozen camera.

Console evidence from the body: repeated `UILock: ... => 00000000 (!!!)`
(gui-common.c's request/state mismatch marker) immediately before a freeze at
SRM allocation.

### The fix

Bail out before issuing the write: if the property is not whitelisted, the
change is known not to happen, and waiting for its ack is pure delay.
Returning 0 keeps the existing "not confirmed" contract for callers — the
same value the caller got before, just 2000 ms sooner.

```c
#ifdef CONFIG_DIGIC_678X
    if (!is_prop_allowed(property))
        return 0;
#endif
```

### Test evidence

- Builds clean for 6D2.111 on `dev` + this commit (gcc-arm-embedded 15.2.1,
  `ML_MODULES="raw_video/mlv_lite file_man bench dual_iso"`).
- **Confirmed on a real 6D2 (2026-08-15, movie LiveView raw-video session).**
  Before the fix: enabling raw video froze the camera in an apparent livelock
  with continuous `UILock: ... (!!!)` console spam (each denied
  `PROP_ICU_UILOCK` write burned the full 2000 ms timeout inside mlv_lite's
  buffer-realloc polling loop; battery pull required). With the fix: the same
  denied writes return instantly (console shows single
  `UILock: 00000000 -> 41000001 => 00000000 (!!!)` lines with no stall), the
  camera stayed responsive through repeated mlv_lite alloc/free cycles, and a
  25-frame 1920x1080 raw MLV was recorded and finalized correctly — the first
  ML raw video captured on this body. Recording behavior itself (early stop on
  buffer exhaustion) is a separate, pre-existing topic unrelated to this fix.

### Risk analysis

- Guarded by `CONFIG_DIGIC_678X`; zero effect on older ports
  (`is_prop_allowed()` only exists under the same guard).
- No new property writes are issued anywhere; the change only waits less.
- Return value for the denied case is unchanged (0 = not confirmed); only the
  latency of that answer changes. A caller that relied on the timeout as an
  implicit `msleep(2000)` would change timing — no such caller is known, and
  relying on that would be a bug in the caller.
- Affects every D678 body with a non-whitelisted property write in a hot
  path, not just 6D2 — that is the point: the whitelist design makes denied
  writes silent, and this makes them at least cheap.
```

## Exact push commands for Chris

```sh
cd "/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/ml"   # = magiclantern_simplified (symlink)

# one-time: add your fork as a remote (create the fork on GitHub first)
git remote add fork git@github.com:<YOUR_GITHUB_USER>/magiclantern_simplified.git

git push fork d678-prop-wait-denied

gh pr create --repo reticulatedpines/magiclantern_simplified \
  --base dev --head <YOUR_GITHUB_USER>:d678-prop-wait-denied \
  --title "property: don't wait out the timeout on writes denied by the whitelist (D678)" \
  --body-file <(sed -n '/^```markdown$/,/^```$/p' \
      "/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/.planning/prs/PR-2-prop-wait-denied.md" \
      | sed '1d;$d')
```

The on-camera retest is done (2026-08-15 16:12, see Test evidence) — this PR
is ready to post as-is.
