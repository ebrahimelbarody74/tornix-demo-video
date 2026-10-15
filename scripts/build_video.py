#!/usr/bin/env python3
"""Assemble the final demo video from the config.

usage: python3 -I build_video.py <config.json> <workdir>   (run render_gfx.js first)

Per clip: crop the browser chrome + Dock away, optional zoom windows (hard switch, on the ORIGINAL timeline),
speed-up, silent PAD (frozen frame) at both ends, placed inside the section's branded frame.
Clips are joined with transitions that only ever overlap the silent pads, so no spoken word is ever cut.
"""
import json, os, subprocess, sys

cfg_path, W = sys.argv[1], sys.argv[2]
cfg = json.load(open(cfg_path))
base = os.path.dirname(os.path.abspath(cfg_path))
G = os.path.join(W, 'gfx-out'); P = os.path.join(W, 'pieces'); os.makedirs(P, exist_ok=True)
SPEED = float(cfg.get('speed', 1.0)); PAD = float(cfg.get('pad_seconds', 0.3)); T = float(cfg.get('transition_seconds', 0.5))
CROP = cfg.get('crop', {'w': 2880, 'h': 1350, 'x': 0, 'y': 238})  # 2880x1748 macOS full-screen recording, Chrome
CRF = str(cfg.get('crf', 24))
assert PAD * 2 >= T, 'transition must fit inside the two silent pads, or words get eaten'

def run(a): subprocess.run(a, check=True)
def dur(f): return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f]).decode())

# frame overlays: the section background with a transparent rounded hole where the video goes
for s in range(len(cfg['sections'])):
    run(['ffmpeg', '-v', 'error', '-y', '-i', f'{G}/bg{s}.png', '-i', f'{G}/mask.png', '-filter_complex',
         'color=black:s=2560x1440,format=gray[c];[1:v]format=gray[m];[c][m]overlay=80:170,negate[a];[0:v]format=rgba[b];[b][a]alphamerge',
         '-frames:v', '1', f'{G}/bgo{s}.png'])

seq, kinds = [f'{P}/intro.mkv'], ['intro']
for i, clip in enumerate(cfg['clips']):
    src = os.path.join(base, clip['path']) if not os.path.isabs(clip['path']) else clip['path']
    out = f'{P}/clip{i:02d}.mkv'; seq.append(out); kinds.append(clip['section'])
    zooms = clip.get('zooms', [])
    n = len(zooms)
    c = CROP
    parts = [f"[0:v]fps=30,crop={c['w']}:{c['h']}:{c['x']}:{c['y']},split={n + 1}" + ''.join(f'[s{k}]' for k in range(n + 1)),
             '[s0]scale=2400:1125:flags=bicubic[z0]']
    cur = '[z0]'
    for k, z in enumerate(zooms, 1):
        h = round(z['w'] * 1125 / 2400 / 2) * 2
        parts.append(f"[s{k}]crop={z['w']}:{h}:{z['x']}:{z['y']},scale=2400:1125:flags=bicubic[q{k}]")
        parts.append(f"{cur}[q{k}]overlay=0:0:enable='between(t,{z['from']},{z.get('to', 99999)})'[z{k}]")
        cur = f'[z{k}]'
    parts.append(f'{cur}setpts=(PTS-STARTPTS)/{SPEED},tpad=start_duration={PAD}:start_mode=clone:stop_duration={PAD}:stop_mode=clone,'
                 'pad=2560:1440:80:170:color=white[v]')
    # second input is a single still image: overlay repeats it, no -loop (a looped image + alphamerge never ends)
    parts.append('[v][1:v]overlay=0:0:format=auto,format=yuv420p[o]')
    atempo = f'atempo={SPEED},' if SPEED != 1.0 else ''
    parts.append(f'[0:a]asetpts=PTS-STARTPTS,highpass=f=80,afftdn=nf=-25,{atempo}aresample=48000,'
                 f'adelay={int(PAD * 1000)}:all=1,apad=pad_dur={PAD}[ao]')
    trim = []
    if 'from' in clip: trim += ['-ss', str(clip['from'])]
    if 'to' in clip: trim += ['-to', str(clip['to'])]
    run(['ffmpeg', '-v', 'error', '-y'] + trim + ['-i', src, '-i', f"{G}/bgo{clip['section']}.png", '-filter_complex', ';'.join(parts),
         '-map', '[o]', '-map', '[ao]', '-r', '30', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '14', '-c:a', 'flac', out])
    print('clip', i, os.path.basename(src), flush=True)

for name, secs in (('intro', cfg.get('intro_seconds', 2.4)), ('outro', cfg.get('outro_seconds', 3.0))):
    run(['ffmpeg', '-v', 'error', '-y', '-framerate', '30', '-i', f'{G}/{name}/%04d.png', '-f', 'lavfi', '-t', str(secs),
         '-i', 'anullsrc=r=48000:cl=mono', '-vf', 'format=yuv420p', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '12',
         '-c:a', 'flac', '-shortest', f'{P}/{name}.mkv'])
seq.append(f'{P}/outro.mkv'); kinds.append('outro')

D = [dur(f) for f in seq]
args = sum((['-i', f] for f in seq), [])
vf, af = [], []
cv, ca, t = '[0:v]', '[0:a]', D[0]
for k in range(1, len(seq)):
    prev, nxt = kinds[k - 1], kinds[k]
    tr = 'fadeblack' if nxt == 'outro' else 'smoothleft' if prev != 'intro' and prev != nxt else 'fade'
    off = t - T
    vf.append(f'{cv}[{k}:v]xfade=transition={tr}:duration={T}:offset={off:.3f}[v{k}]')
    af.append(f'{ca}[{k}:a]acrossfade=d={T}:c1=nofade:c2=nofade[a{k}]')
    cv, ca = f'[v{k}]', f'[a{k}]'
    t = off + D[k]
fc = ';'.join(vf + af) + f';{ca}loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000[af]'
final = os.path.join(base, cfg['output']) if not os.path.isabs(cfg['output']) else cfg['output']
os.makedirs(os.path.dirname(final) or '.', exist_ok=True)
if os.path.exists(final) and '--overwrite' not in sys.argv:
    root, ext = os.path.splitext(final); k = 2
    while os.path.exists(f'{root}-v{k}{ext}'): k += 1
    final = f'{root}-v{k}{ext}'   # never overwrite a version the user already has
run(['ffmpeg', '-v', 'error', '-y'] + args + ['-filter_complex', fc, '-map', cv, '-map', '[af]',
     '-c:v', 'libx264', '-preset', 'slow', '-crf', CRF, '-tune', 'stillimage', '-profile:v', 'high', '-pix_fmt', 'yuv420p',
     '-r', '30', '-g', '300', '-c:a', 'aac', '-b:a', '128k', '-ac', '1', '-movflags', '+faststart', final])
# WhatsApp re-encodes to <=720p at a low bitrate and wrecks small UI text; hand it a clean, sharpened 720p instead
wa = os.path.splitext(final)[0] + '-WhatsApp.mp4'
fc_wa = ';'.join(vf + af) + (f';{cv}scale=1280:720:flags=lanczos,unsharp=5:5:0.6:5:5:0.0,format=yuv420p[vo]'
                             f';{ca}loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000[af]')
run(['ffmpeg', '-v', 'error', '-y'] + args + ['-filter_complex', fc_wa, '-map', '[vo]', '-map', '[af]',
     '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-maxrate', '4M', '-bufsize', '8M', '-tune', 'stillimage',
     '-profile:v', 'high', '-level', '4.0', '-pix_fmt', 'yuv420p', '-r', '30', '-g', '60',
     '-c:a', 'aac', '-b:a', '128k', '-ac', '1', '-movflags', '+faststart', wa])
print(f'WhatsApp {wa}  {os.path.getsize(wa) / 1e6:.1f} MB')
thumb_out = os.path.splitext(final)[0] + '-thumbnail.png'
run(['cp', f'{G}/thumb.png', thumb_out])
print(f'DONE {final}  {t:.1f}s  {os.path.getsize(final) / 1e6:.1f} MB')
print(f'thumbnail {thumb_out}')
