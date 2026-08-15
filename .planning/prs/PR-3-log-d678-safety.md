# PR 3 — log-d678: don't spin forever when the log buffer allocation fails

- **Target repo:** `reticulatedpines/magiclantern_simplified`
- **Target branch:** `dev` (based on `dev` @ `3f24042a4`, current local `origin/dev`)
- **Source branch:** `log-d678-no-brick-spin` (2 commits: `d74951d52` spin fix, `2b32a614d` gcc 15 initializer fix)
- **Files:** `src/log-d678.c` (+17/−2 total)
- **Local branch location:** the `magiclantern_simplified` clone in this project (note: `magiclantern_simplified` is a symlink to `ml/`); worktree with the built tree at `/home/chris/ml6d2/trackC-wt3`
- **Patch files (durability copies):** `.planning/prs/0001-log-d678-don-t-spin-forever-when-the-log-buf.branch3.patch`, `.planning/prs/0002-log-d678-make-room-for-the-NUL-in-task_name_.branch3.patch`

## Title

```
log-d678: don't spin forever when the log buffer allocation fails
```

## PR body (ready to paste)

```markdown
### Commit 1 — the safety fix

`log_start()` ended with `while (!buf);`. On models that allocate the logging
buffer with `_AllocateMemory()` (everything without a hardcoded address), an
allocation failure therefore hangs `boot_post_init_task` in an infinite loop —
no LED activity, no display, indistinguishable from a bricked camera. For a
diagnostic logger whose whole audience is people bringing up new ports, "looks
bricked on failure" is the worst possible failure mode.

**The failure is reachable, not theoretical.** With this logger wired into a
full 6D2.111 ML build, `GetMemoryInformation()` reported 0 total / 0 free at
`log_start()` time and every `_AllocateMemory()` from 2 MB down to 128 KB
failed — measured through the qemu monitor via before/after pool counters
compiled into the build, reproduced on four consecutive builds. (Why that
build config exhausts the pool is a separate, still-open investigation; it
does not change the conclusion that the allocation can fail.)

The fix: on allocation failure, set `buf_size = 0` and return before patching
DebugMsg or installing the ISR hooks. `my_DebugMsg()` already drops everything
while `buf` is NULL, and `log_finish()` now returns early in the same case —
nothing was installed, so there is nothing to undo and nothing to save. The
camera then boots normally, just without a startup log. Losing the log is the
cheaper failure.

Models with hardcoded buffer addresses (80D, 5D4, 200D) are unaffected —
`buf` is a constant there and the branch is never taken.

### Commit 2 — gcc 15 build fix (separable; drop it if unwanted)

`char task_name_padded[11] = "           ";` (11 spaces) leaves no room for
the terminator. Not a runtime bug — the `snprintf` below always writes a NUL
before the first read — but gcc 15 rejects the initializer under
`-Werror=unterminated-string-initialization`:

    src/log-d678.c:70:33: error: initializer-string for array of 'char'
    truncates NUL terminator but destination lacks 'nonstring' attribute
    (12 chars into 11 available)

so the file no longer compiles with current toolchains at all. Sizing the
array `[12]` fixes it. Verified A/B with gcc-arm-embedded 15.2.1 under the
6D2 platform flags: fails without this commit, compiles clean with it.

### Test evidence

- Full 6D2.111 build on `dev` + both commits passes (gcc-arm-embedded 15.2.1).
  Note this build does not itself compile `log-d678.c` — no in-tree build
  currently wires it in — so additionally:
- `log-d678.o` was compiled standalone under the exact 6D2 platform CFLAGS
  (`-Werror`, gcc 15.2.1) via a temporary local Makefile hook: compiles clean
  with both commits, fails without commit 2 (error above).
- The bail-out path itself matches what was observed live: in the failing
  builds described above, a NULL `buf` run completed boot normally with no
  `DEBUGMSG.LOG` written, instead of hanging.

### Risk analysis

- Behavior change only on the path that previously hung forever; every
  successful-allocation path is byte-identical.
- The `log_finish()` early return also guards the `dump_file(NULL, 0)` call
  that the old code could only reach in theory (it could never get past the
  spin).
- The neighbouring dead check `if (!(read_cpsr() & 80))` (decimal 80 = 0x50,
  overlaps CPSR M[4], set in every AArch32 mode, so it can never fire) is
  deliberately left untouched — making it live is a separate discussion.
```

## Notes for Chris (not part of the PR body)

- **The HANDOFF.json "collapse the vestigial #ifdef at log-d678.c:346-350"
  decision is satisfied by construction:** that vestigial no-op `#ifdef` exists
  only in our local capture patch (`patches/0002`), left over from a reverted
  retry loop. This branch is based on clean upstream `dev`, which has a single
  `_AllocateMemory` call — there is nothing to collapse and the branch diff
  contains no `#ifdef CONFIG_STARTUP_LOG` at all.
- **The `GetFreeMemForAllocateMemory` duplicate-definition guard from
  `patches/0002` is deliberately left out.** It only matters when `log-d678.o`
  is linked into a **full** ML build, where `src/mem.c` also defines that
  function. No in-tree upstream build wires `log-d678.o` in today, so the
  conflict is unreachable upstream; the guard belongs to whatever future PR
  adds a `CONFIG_STARTUP_LOG` build hook (our `patches/0002`), not to this
  safety fix.

## Exact push commands for Chris

```sh
cd "/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/ml"   # = magiclantern_simplified (symlink)

# one-time: add your fork as a remote (create the fork on GitHub first)
git remote add fork git@github.com:<YOUR_GITHUB_USER>/magiclantern_simplified.git

git push fork log-d678-no-brick-spin

gh pr create --repo reticulatedpines/magiclantern_simplified \
  --base dev --head <YOUR_GITHUB_USER>:log-d678-no-brick-spin \
  --title "log-d678: don't spin forever when the log buffer allocation fails" \
  --body-file <(sed -n '/^```markdown$/,/^```$/p' \
      "/home/chris/Vibe Coding/6D Mark II Magic Lantern 6D2/.planning/prs/PR-3-log-d678-safety.md" \
      | sed '1d;$d')
```
