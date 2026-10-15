---
name: tornix-demo-video
description: Turn a set of raw screen recordings of a product walkthrough (macOS, Chrome, spoken Arabic) into one branded demo video — thumbnail as the first frame with a short animation, a purple branded frame with a section title and step chips, zooms on the key moments, silent-padded transitions that never cut a word, an animated outro, and a WhatsApp-tuned 720p copy. Use when the user sends several .mov screen recordings and says things like «ادمجهم فيديو واحد», «اعمل الصورة في الأول», «الجودة تبقى عالية والحجم يقل», «اعمل مونتاج», «فيديو شرح الميزة», «make one video from these recordings», or asks for a script before recording one («اكتبلي اسكربت أصوّر بيه»). Also use to rebuild a video after the user swaps one recording for another.
---

# Tornix demo video

Raw screen recordings → one branded, readable, WhatsApp-safe walkthrough video.
Pipeline: **inspect → write config → render graphics → build → verify → WhatsApp copy**.

## Hard rules (each one came from a real correction)

1. **Never cut the user's speech.** No silence removal, no trimming false starts, no "tightening" — unless the user
   asks for that specific cut. «مش عايز قص… عايز نفس اللي بعتهولك». Transitions only overlap the silent pads
   `build_video.py` adds (`pad_seconds * 2 >= transition_seconds` is asserted).
2. **Never overwrite a version the user already has.** Every rebuild gets a new file name (`-v2`, `-v3`…);
   the script does this automatically unless `--overwrite`.
3. **Ask once before sending audio to Groq** (third party). After a yes, it's fine for the rest of the job.
4. **Verify by transcribing the FINAL file**, not the inputs: every sentence from the recordings must be in it.
   Whisper sometimes skips a long stretch on a full file — re-transcribe that window alone before concluding
   words are missing.
5. **WhatsApp ruins small text.** It re-encodes any video to ≤720p at a low bitrate. Always also ship the
   `-WhatsApp` copy (step 6) and tell the user to press **HD** when sending (or send as Document for full quality).
6. Keep the style the user approved; when they say «نفس الاستايل بس الجودة أعلى», change encoding only.
7. A clip named in the request that is NOT in the video usually maps to a renamed/trimmed copy that is
   (e.g. `ee.mov` was a trim of `Screen Recording … 10.46.44.mov`) — check durations/content, then say which one you replaced.

## 1. (Optional) Script before recording

If the user wants to record first, write the narration script in plain Egyptian Arabic, as scenes:
screen → what to do → what to say, ~4–5 min total. Include a prep list (1920×1080+, browser zoom 125%, close
other tabs, close-by mic, seed data) and "if you make a mistake, pause 3 s and repeat the sentence — I'll cut it"
(only when they have agreed to cuts). Put the script in the chat when asked «اكتب الكلام هنا».

## 2. Inspect the recordings

```bash
bash ~/.claude/skills/tornix-demo-video/scripts/inspect.sh <workdir> rec1.mov rec2.mov …
```
Prints duration, a Groq Whisper transcript with timestamps, and writes `inspect/cN-tiles.jpg`
(1 tile per second, 6 per row) — Read the tiles to find when each screen appears (for zoom windows).
Use **bash** for loops/word-splitting: zsh does not split `$var` (`for s in "2 3"; set -- $s` breaks).

Default crop `2880x1350+0+238` = a full-screen 2880×1748 macOS recording of Chrome with a bookmarks bar,
minus browser chrome and the Dock. If the window differs, measure: `crop=2880:60:0:<y>` strips around the edges.

## 3. Write the config

Copy `examples/atlas-auto-close.json` and edit:
- `sections` — one per title shown in the frame; `step` (1..n) highlights that step chip, `all_done: true` = summary.
- `steps` — the chip labels under the video.
- `clips` — in order: `path`, `section`, optional `zooms` `[{from, to?, x, y, w}]` in the crop's pixel space
  on the clip's ORIGINAL timeline (h is derived from the 2400×1125 slot). Zoom the moments that prove the story:
  the prompt typed to Atlas, the chat message, the «أغلقها أطلس» card. `from`/`to` on a clip trims it — only if asked.
- `thumbnail` — `headline` (`[[words]]` get the brand gradient), `subtitle` (`\n` = line break), two `chips`,
  `card_image` = a crop of the strongest UI moment (`ffmpeg -ss T -i clip -frames:v 1 -vf crop=…`).
- `speed` (1.12 = what the user asked for once; 1.0 = untouched), `output`.

## 4. Render graphics

```bash
node ~/.claude/skills/tornix-demo-video/scripts/render_gfx.js <config.json> <workdir>
```
Playwright screenshots `assets/gfx.html` → `gfx-out/` (section frames, rounded mask, `thumb.png`, intro/outro
frames at 30 fps). Read `gfx-out/thumb.png` and one `bgN.png` before building. Set `PLAYWRIGHT_MODULE` if
Playwright isn't found.

## 5. Build

```bash
python3 -I ~/.claude/skills/tornix-demo-video/scripts/build_video.py <config.json> <workdir>
```
~5 min for ~2 min of video on a loaded machine — run it in the background. Output: 2560×1440 H.264
(`-tune stillimage`, CRF 24 ≈ 11 MB for 2 min) + `<name>-thumbnail.png`.
Sanity check a piece's frame count (`ffprobe -count_packets`) if a step runs long: a looped still image fed to
`alphamerge` never ends (one piece produced 27k frames before it was killed) — the script uses a single
still + `overlay` instead.

## 6. WhatsApp copy

Re-encode from the high-quality pieces (not the CRF-24 file): `scale=1280:720:flags=lanczos,unsharp=5:5:0.6`,
`-crf 17 -maxrate 4M -bufsize 8M -tune stillimage -g 60` → `<name>-WhatsApp.mp4` (~15 MB for 2 min).
Tell the user: press **HD** in WhatsApp, or send as Document to keep 1440p.

## 7. Verify and report

- Transcribe the final file (rule 4); Read 2–3 frames at full size (a zoom, a frame with small text).
- Report: path(s), duration, size, what changed vs the previous version, what's still applied (e.g. 1.12× speed).

## Files

- `scripts/inspect.sh` — durations, per-second tiles, Groq transcript.
- `scripts/render_gfx.js` — branded graphics from the config.
- `scripts/build_video.py` — pieces → transitions → final + thumbnail.
- `assets/gfx.html` — the frame / thumbnail / outro design (2560×1440, RTL, Thmanyah). `.scene{overflow:hidden}`
  is load-bearing: in RTL an element hanging off the left edge shifts the whole screenshot.
- `assets/` — Tornix mark + wordmark, Atlas figures (`idle`, `celebrating`, `explaining`), Thmanyah weights.
- `examples/atlas-auto-close.json` — the config of the first video made with this skill.
