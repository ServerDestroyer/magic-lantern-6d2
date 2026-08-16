# Draft retraction — the "first-ever raw video on a 6D2" claim (NOT POSTED — needs Chris)

**What this is:** a short correction of the "first-ever raw video on a 6D2"
claim, which the maintainer rejected as over-claiming. Leaving it uncorrected is
what casts doubt on the true results (the MPU spells, the interrupt fix, the
fps-header fix), so the record is worth setting straight plainly and then moving
on.

**Where to post it:** in the same place the original claim was made — the same
forum thread or GitHub comment. Post it as its own short message; do not bury it
in an unrelated PR. If the original claim lived in more than one place, the same
text works verbatim in each.

**Grounding (all from spike 006, hardware-verified):**
- Upstream already ships a 6D2 `mlv_lite` implementation. Its own commit message
  (`fd11ca5040`, "6D2: broken mlv_lite implementation") says it "mostly hangs cam
  or reboots… Rarely however, real frames are captured." So raw frames on this
  body are not unprecedented — "first-ever" is simply wrong.
- What is actually true: valid, finalized MLV files captured on one body —
  `M15-1612.MLV` is 25 uncompressed 14-bit 1920×1080 frames, videoFrameCount=25,
  pixel-valid on decode; later runs produced longer finalized takes. That is a
  reliability gain over a known-broken baseline, not a new capability.
- It is not usable raw video: at 1080p60 14-bit the write demand (~217 MB/s) far
  exceeds the UHS-I bus (~104 MB/s), so it buffer-fills and stops after ~0.4 s.
  Usable capture needs lower resolution, lower frame rate, or working compression
  (the 10/12-bit menu options are non-functional on the 6D2).

---

```markdown
A correction to something I posted earlier. I described a raw video capture on
the EOS 6D Mark II as a "first-ever," and that was an overstatement I should not
have made.

mlv_lite already has a 6D2 implementation in-tree. Its own commit message
(fd11ca5040) describes it as mostly hanging or rebooting the camera, while noting
that real frames are captured on rare occasions. So raw frames on this body are
not unprecedented, and framing my result as a first was wrong.

What I actually have is narrower, and I'll state it precisely: on one body I
captured MLV files that are structurally valid and finalized — a 25-frame
uncompressed 14-bit 1920x1080 clip, and longer takes in later runs — against an
upstream baseline for the same code that "mostly hangs." That is a reliability
improvement over a known-broken starting point, not a new capability. It is also
not usable raw video: at 1080p60 14-bit the write demand (~217 MB/s) is well
above the UHS-I bus (~104 MB/s), so recording buffer-fills and stops after a
fraction of a second. Usable capture would need lower resolution, a lower frame
rate, or working compression.

Apologies for the overstatement. I would rather the record be accurate, since an
inflated claim in one place undercuts trust in the parts that do hold up. Happy
to share the files, md5s, and frame-level analysis for anyone who wants to check.
```

## If Chris wants this

1. Post the block above wherever the original "first-ever" claim was made.
2. Nothing else is required. It is a standalone correction, not tied to any PR.
3. It deliberately does not re-argue or hedge — it withdraws the claim, states
   what is true, offers the evidence, and stops.
