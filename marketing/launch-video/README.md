# CareGist launch video

A 60-second, 1920×1080 launch film for the two current offers, showing how each leads to the next:

**Territory Opportunity Brief** (decide which providers to focus on) → **Weekly Digest** (keep the shortlist current, shown by enquiry only) → new movement leads to the next **Brief**.

Product facts follow `docs/manuals/SALES_GTM_MANUAL.md` (15 Oct 2026). Every sample row on screen is fictional and labelled as illustrative. The story order and claims follow a founder review on 19 October 2026 (see "Claims" below).

## Pipeline

| Step | Tool | Command (from this folder) |
| --- | --- | --- |
| 1. Map data | Python | `python3 data/prepare_points.py` reads `../../directory_providers.csv` and writes `data/points.json` |
| 2. 3D map shot | Blender 5.2 | `/Applications/Blender.app/Contents/MacOS/Blender -b -P blender/build_map.py -- --render`, then `ffmpeg -framerate 30 -i renders/map/frame_%04d.png -c:v libx264 -pix_fmt yuv420p -crf 14 renders/map.mp4` |
| 3. Score | Python + numpy | `python3 data/make_score.py` writes `remotion/public/score.wav` |
| 4. Edit | Remotion 4 | `cp renders/map.mp4 remotion/public/ && cd remotion && npm install && npm run render` |

Output: `renders/caregist-launch.mp4`. Use `npm run studio` to preview and tweak timing (`BEATS` in `remotion/src/Launch.tsx`).

## Beats

| Time | Frames | Beat | Source |
| --- | --- | --- | --- |
| 0–5 s | 0–150 | 55,000+ CQC-registered locations sweep in | Blender |
| 5–9 s | 150–270 | "You sell into care…" questions | Remotion + Higgsfield b-roll |
| 9–14 s | 270–420 | Step one: Territory Opportunity Brief; camera dives, shortlist rises | Blender (map frames 270–420) |
| 14–27 s | 420–810 | PDF / CSV / source manifest, £745 once | Remotion |
| 27–30 s | 810–900 | Bridge: "Got your shortlist? Keep it current." Brief → Digest | Remotion |
| 30–34 s | 900–1020 | Step two, by enquiry: Weekly Digest; West Midlands lights up | Blender (map frames 150–270) |
| 34–46 s | 1020–1380 | Digest issues 1–4, new registrations only, "By enquiry" | Remotion |
| 46–53 s | 1380–1590 | The loop: Brief → Digest → next Brief | Remotion |
| 53–60 s | 1590–1800 | Logo, caregist.co.uk, compliance line | Remotion |

The score (`data/make_score.py`) mirrors these cuts in `CUTS`. Chords change at 0, 270, 810, 1020 and 1380, and the heartbeat pulse runs under the Digest (900–1380). Regenerate it whenever `BEATS` changes.

## Claims (founder review, 19 Oct 2026)

- **Weekly Digest is on sales hold.** It is shown "by enquiry" with no price, and labelled step two, not step one.
- **Rating changes are never named.** The Digest card shows new registrations only (fictional names). The map legend keeps an unnamed "Rating changes" dot.
- **No dated rating-change promise.** The Digest offers "New registrations, each with its CQC registration date" and "Published rating changes, linked to the CQC report". Production rating events currently lack dates.
- **No CRM promise.** The CSV card says "Provider and location IDs, as a CSV".
- **"Every CQC-registered location in England" / "55,000+ locations".** The register includes dentists, GP surgeries and hospitals. Live active count was 57,159 on 19 October.
- **Full product name.** "Territory Opportunity Brief" is used throughout.
- **Footer.** Independent of CQC; providers to focus on, not leads ready to buy; Brief fee as published; no VAT charged; terms confirmed before any order.

## Higgsfield b-roll

The question beat uses `remotion/public/broll-question.mp4`. It was generated on 19 Oct 2026 through the Higgsfield integration in the ChatGPT/Codex app with Kling 3.0 Standard (silent, 720p, 5 s, 16:9, quoted at 7.5 credits). It plays blurred and darkened because the map on the laptop is invented, not England. Set `QUESTION_BROLL` in `Launch.tsx` to `null` to fall back to type only. Prompt:

> Cinematic slow push-in, a UK sales manager at a wooden desk at dusk reviewing a laptop that shows a glowing map of England, warm lamp light, terracotta, deep brown and amber palette, shallow depth of field, calm and thoughtful mood. No visible text, no logos, no readable screen UI.

Seedance 2.5 at 1080p was quoted at 80 credits, so the cheaper Kling setting was used.

## Before publishing

The copy changed after the founder review on 19 October 2026 and needs founder re-approval before posting. If the Digest comes off sales hold, update its "By enquiry" beat and re-check the claims above.
