# CareGist launch video

A 60-second, 1920×1080 launch film for the two current offers, showing how each leads to the next:

**Weekly Digest** (spot what changed in a region) → **Territory Opportunity Brief** (decide which accounts to investigate) → back to the **Digest** (keep the shortlist current).

Product facts follow `docs/manuals/SALES_GTM_MANUAL.md` (15 Oct 2026). Every sample row on screen is fictional and labelled as illustrative.

## Pipeline

| Step | Tool | Command (from this folder) |
| --- | --- | --- |
| 1. Map data | Python | `python3 data/prepare_points.py` reads `../../directory_providers.csv` and writes `data/points.json` |
| 2. 3D map shot | Blender 5.2 | `/Applications/Blender.app/Contents/MacOS/Blender -b -P blender/build_map.py -- --render`, then `ffmpeg -framerate 30 -i renders/map/frame_%04d.png -c:v libx264 -pix_fmt yuv420p -crf 14 renders/map.mp4` |
| 3. Score | Python + numpy | `python3 data/make_score.py` writes `remotion/public/score.wav` |
| 4. Edit | Remotion 4 | `cp renders/map.mp4 remotion/public/ && cd remotion && npm install && npm run render` |

Output: `renders/caregist-launch.mp4`. Use `npm run studio` to preview and tweak timing (`BEATS` in `remotion/src/Launch.tsx`).

## Beats

| Time | Beat | Source |
| --- | --- | --- |
| 0–5 s | 55,000+ CQC locations sweep in | Blender |
| 5–9 s | "You sell into care…" questions | Remotion (Higgsfield b-roll slot) |
| 9–13 s | Step one: Weekly Digest, West Midlands lights up | Blender |
| 13–25 s | Digest issues 1–4, £150 once | Remotion |
| 25–28 s | Bridge: Digest → Brief | Remotion |
| 28–33 s | Step two: Brief, camera dives, shortlist rises | Blender |
| 33–46 s | PDF / CSV / manifest, £745 once | Remotion |
| 46–53 s | The loop: each one leads to the next | Remotion |
| 53–60 s | Logo, caregist.co.uk, compliance line | Remotion |

## Higgsfield b-roll

The question beat uses `remotion/public/broll-question.mp4`. It was generated on 19 Oct 2026 through the Higgsfield integration in the ChatGPT/Codex app with Kling 3.0 Standard (silent, 720p, 5 s, 16:9, quoted at 7.5 credits). It plays blurred and darkened because the map on the laptop is invented, not England. Set `QUESTION_BROLL` in `Launch.tsx` to `null` to fall back to type only. Prompt:

> Cinematic slow push-in, a UK sales manager at a wooden desk at dusk reviewing a laptop that shows a glowing map of England, warm lamp light, terracotta, deep brown and amber palette, shallow depth of field, calm and thoughtful mood. No visible text, no logos, no readable screen UI.

Seedance 2.5 at 1080p was quoted at 80 credits, so the cheaper Kling setting was used.

## Before publishing

The Digest is still on sales hold (see the sales manual). Get founder sign-off on the public claims and prices before posting.
