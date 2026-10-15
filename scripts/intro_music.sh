#!/bin/bash
# Intro sting for the thumbnail, ~3.6 s.
#   intro_music.sh synth <out.wav>              FREE (default): synthesized with ffmpeg — riser, sub hit, pad, pluck arpeggio
#   intro_music.sh ai    <out.wav> [prompt]     PAID: Google Lyria 3.5 on fal.ai via genmedia (~$0.10 per generation,
#                                               billed to the user's FAL key) — run ONLY when the user asked for it and
#                                               agreed to the price
set -e
MODE="${1:-synth}"; OUT="$2"
[ -z "$OUT" ] && { echo "usage: intro_music.sh synth|ai <out.wav> [prompt]"; exit 1; }

if [ "$MODE" = "synth" ]; then
  HIT=1.05   # the "hit" lands as the thumbnail shine passes
  PAD="(sin(2*PI*220*t)+0.8*sin(2*PI*277.18*t)+0.7*sin(2*PI*329.63*t)+0.45*sin(2*PI*493.88*t)+0.3*sin(2*PI*440.6*t))*0.11*gte(t,$HIT)*(1-exp(-(t-$HIT)*7))*exp(-(t-$HIT)*0.85)"
  pl() { echo "0.2*gte(t,$1)*(1-exp(-(t-$1)*180))*sin(2*PI*$2*t)*exp(-(t-$1)*6.5)"; }
  ARP="$(pl 1.10 659.25)+$(pl 1.24 880)+$(pl 1.38 1108.73)+$(pl 1.52 1318.51)+$(pl 1.80 1760)"
  SUB="0.55*gte(t,$HIT)*(1-exp(-(t-$HIT)*120))*sin(2*PI*(55+30*exp(-(t-$HIT)*20))*t)*exp(-(t-$HIT)*4.5)"
  ffmpeg -v error -y \
    -f lavfi -i "aevalsrc=exprs='$PAD+$ARP+$SUB':s=48000:d=3.6" \
    -f lavfi -i "anoisesrc=color=pink:r=48000:d=3.6:a=0.5" \
    -filter_complex "[1:a]highpass=f=500,lowpass=f=7000,volume='0.55*pow(min(t/$HIT,1),2.2)*if(lt(t,$HIT),1,exp(-(t-$HIT)*7))':eval=frame[w];\
[0:a][w]amix=inputs=2:normalize=0,aecho=0.8:0.6:70|140:0.25|0.15,alimiter=limit=0.89,afade=t=out:st=2.0:d=1.1,pan=stereo|c0=c0|c1=c0" \
    -ac 2 "$OUT"
elif [ "$MODE" = "ai" ]; then
  PROMPT="${3:-A 4-second modern tech product intro sting: soft rising whoosh, a bright synth pluck arpeggio, a warm pad chord and a deep sub hit at 1 second, clean and optimistic, no vocals, ends with a short reverb tail}"
  command -v genmedia >/dev/null || { echo "genmedia CLI not installed (see the genmedia skill)"; exit 1; }
  TMP=$(mktemp -d)
  genmedia run google/lyria-3.5 --prompt "$PROMPT" --download "$TMP/{request_id}.{ext}" --json > "$TMP/run.json"
  SRC=$(ls "$TMP"/*.mp3 "$TMP"/*.wav 2>/dev/null | head -1)
  [ -z "$SRC" ] && { cat "$TMP/run.json"; exit 1; }
  ffmpeg -v error -y -i "$SRC" -t 3.6 -af "afade=t=out:st=2.0:d=1.1" -ar 48000 -ac 2 "$OUT"
else
  echo "mode must be synth or ai"; exit 1
fi
echo "intro music -> $OUT"
