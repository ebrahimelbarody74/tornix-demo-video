# tornix-demo-video

A Claude Code skill that turns raw screen recordings of a product walkthrough into one branded demo video:

- the **thumbnail is the first frame**, followed by a short animation
- a purple **branded frame** around the screen, with a section title on top and step chips underneath
- **zooms** on the key moments so UI text stays readable
- **transitions only over silent padding**, so no spoken word is ever cut
- a short **intro music sting** — free (synthesized with ffmpeg) by default, or paid AI music (Lyria 3.5 on fal.ai) as an option
- an animated **outro**
- a **WhatsApp-tuned 720p copy** (sharpened, high bitrate) alongside the 1440p master

Built for Tornix feature demos (Arabic narration, RTL, Thmanyah font), but every text, title and clip comes from one JSON config.

## Install

```bash
git clone https://github.com/ebrahimelbarody74/tornix-demo-video ~/.claude/skills/tornix-demo-video
```

Requires `ffmpeg` (with libx264), `node` + Playwright (Chromium), `python3`, and optionally a `GROQ_API_KEY` for transcripts.

## Use

Ask Claude Code something like «ادمج التسجيلات دي في فيديو واحد واعمل الصورة في الأول». Or run the steps by hand:

```bash
bash scripts/inspect.sh work rec1.mov rec2.mov …         # durations, per-second tiles, transcript
cp examples/atlas-auto-close.json my-video.json          # edit titles, steps, clips, zooms, thumbnail
node scripts/render_gfx.js my-video.json work            # frames, thumbnail, intro/outro
python3 -I scripts/build_video.py my-video.json work     # final.mp4 + -WhatsApp.mp4 + -thumbnail.png
```

See `SKILL.md` for the full workflow and the rules behind it.

## Assets

The Tornix logo, the Atlas character images and the Thmanyah font files in `assets/` belong to their respective owners and are included only to render Tornix videos.
