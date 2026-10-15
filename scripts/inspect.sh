#!/bin/bash
# Look at screen recordings before editing: duration/size, a 1-frame-per-second contact sheet, and a
# Groq Whisper transcript with segment timestamps.
# usage: inspect.sh <workdir> <clip1.mov> [clip2.mov ...]
# Sends AUDIO to Groq — ask the user once before the first run (their voice goes to a third party).
set -e
W="$1"; shift
mkdir -p "$W/inspect"
KEY="${GROQ_API_KEY:-$(grep -h '^GROQ_API_KEY=' "$HOME/tornix-ai/.env.local" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"'"'")}"
i=1
for f in "$@"; do
  echo "=== c$i  $(basename "$f")"
  ffprobe -v error -show_entries stream=codec_type,width,height,r_frame_rate:format=duration -of compact=p=0 "$f"
  ffmpeg -v error -y -i "$f" -vf "fps=1,crop=2880:1350:0:238,scale=480:-1,tile=6x8" -frames:v 1 "$W/inspect/c$i-tiles.jpg"
  ffmpeg -v error -y -i "$f" -vn -ac 1 -ar 16000 -c:a libopus -b:a 24k "$W/inspect/c$i.ogg"
  if [ -n "$KEY" ]; then
    curl -s https://api.groq.com/openai/v1/audio/transcriptions -H "Authorization: Bearer $KEY" \
      -F model=whisper-large-v3 -F language=ar -F response_format=verbose_json \
      -F "prompt=شرح بالعامية المصرية لنظام Tornix وأطلس والمهام" -F "file=@$W/inspect/c$i.ogg" > "$W/inspect/c$i.json"
    python3 -I -c "
import json,sys
d=json.load(open(sys.argv[1]))
for s in d.get('segments',[]): print(f\"  {s['start']:6.1f}-{s['end']:6.1f} {s['text'].strip()}\")
" "$W/inspect/c$i.json"
  fi
  echo "  tiles: $W/inspect/c$i-tiles.jpg  (tile n = second n, 6 per row)"
  i=$((i+1))
done
