# Draft comment for upstream PR #223 (NOT POSTED — needs Chris)

Target: https://github.com/reticulatedpines/magiclantern_simplified/pull/223
(evgeniimv, "issue-221 add FEATURE_LV_FOCUS_BOX_AUTOHIDE to features list in 6D2",
open since 2025-08-31, one-line change to `platform/6D2.111/features.h`, hardware
tested by its author, no maintainer response yet.)

Why it is worth posting: it is a stale PR from another 6D2 owner, and the thing
that would most obviously unstick it is a second body confirming the feature.
We have the build loop and the camera. Posting it is a soft commitment to
actually run the test, so it is Chris's call, not mine — an assistant should not
promise someone else's time on a public thread.

Blocked when attempted from this session by the harness classifier; not worked
around on purpose.

---

```markdown
Second 6D2 owner here, with a build-and-test loop already running against 1.1.1 —
I would be glad to give this an independent confirmation on a different body if
that helps it move.

For what it is worth from this side: `FEATURE_LV_FOCUS_BOX_AUTOHIDE` only reaches
`src/tweaks.c` (the guard at :1136 and the handling at :1995/:2033), so the change
is confined to code that several other ports already enable, which matches the
one-line diff here.

On the `EFLensComTask: stack warning: free=232 used=792` you saw — that is ML's own
stack monitor rather than anything this feature does, and it is a warning about
headroom, not a fault. Worth separating from this PR so it does not hold the
feature up.

I will build it on top of my current 6D2 tree and report back with results from a
second body — including whether the warning reproduces here, which would tell you
whether it is body-specific or general to the port.
```

## If Chris wants this

1. Post the comment above.
2. Then actually do it: add `#define FEATURE_LV_FOCUS_BOX_AUTOHIDE` to
   `ml/platform/6D2.111/features.h`, rebuild (remember the double module-staleness
   gate), sync the card, and check the focus box hides in LiveView.
3. Report back on the PR with the result either way. An honest "does not work on
   my body" is as useful to the maintainer as a confirmation.
