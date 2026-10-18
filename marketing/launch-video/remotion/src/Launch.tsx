import React from "react";
import {
  AbsoluteFill,
  Audio,
  Easing,
  OffthreadVideo,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { C, SANS, SERIF, fontFaces } from "./theme";

/*
 * Story: the Weekly Digest shows what changed in a region; that movement is the
 * reason to commission a Territory Opportunity Brief; the Brief's shortlist is
 * then kept current by the Digest. Product facts follow
 * docs/manuals/SALES_GTM_MANUAL.md (15 Oct 2026). Every sample row on screen is
 * fictional and labelled as illustrative.
 */

// Beat timeline (frames @30fps). Map frames refer to renders/map.mp4.
const BEATS = {
  reveal: { from: 0, dur: 150, map: 0 },
  question: { from: 150, dur: 120 },
  digestMap: { from: 270, dur: 120, map: 150 },
  digestUi: { from: 390, dur: 360 },
  bridge: { from: 750, dur: 90 },
  briefMap: { from: 840, dur: 150, map: 270 },
  briefUi: { from: 990, dur: 390 },
  loop: { from: 1380, dur: 210 },
  cta: { from: 1590, dur: 210 },
};
export const TOTAL_FRAMES = 1800;

// Optional Higgsfield b-roll for the question beat; null keeps the type-only version.
const QUESTION_BROLL: string | null = "broll-question.mp4"; // Higgsfield, Kling 3.0, 720p

const ease = Easing.bezier(0.22, 1, 0.36, 1);

const useIn = (delay = 0, dur = 24) => {
  const f = useCurrentFrame();
  return interpolate(f - delay, [0, dur], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ease });
};

const useOut = (dur: number, len = 12) => {
  const f = useCurrentFrame();
  return interpolate(f, [dur - len, dur], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
};

const Rise: React.FC<{ delay?: number; y?: number; children: React.ReactNode; style?: React.CSSProperties }> = ({
  delay = 0,
  y = 28,
  children,
  style,
}) => {
  const p = useIn(delay);
  return <div style={{ opacity: p, transform: `translateY(${(1 - p) * y}px)`, ...style }}>{children}</div>;
};

const Kicker: React.FC<{ children: React.ReactNode; color?: string }> = ({ children, color = C.amber }) => (
  <div style={{ fontFamily: SANS, fontWeight: 600, fontSize: 22, letterSpacing: 5, textTransform: "uppercase", color }}>
    {children}
  </div>
);

const Fine: React.FC<{ children: React.ReactNode; color?: string; style?: React.CSSProperties }> = ({
  children,
  color = "rgba(245,239,228,0.55)",
  style,
}) => <div style={{ fontFamily: SANS, fontSize: 18, color, letterSpacing: 0.3, ...style }}>{children}</div>;

const MapClip: React.FC<{ startFrom: number; dur: number }> = ({ startFrom, dur }) => (
  <OffthreadVideo src={staticFile("map.mp4")} startFrom={startFrom} endAt={startFrom + dur} muted />
);

const Vignette = () => (
  <AbsoluteFill
    style={{
      background:
        "linear-gradient(90deg, rgba(20,16,13,0.88) 0%, rgba(20,16,13,0.55) 32%, transparent 58%), radial-gradient(ellipse at 60% 50%, transparent 40%, rgba(20,16,13,0.85) 100%)",
    }}
  />
);

/* ---------- 1. Reveal ---------- */
const Reveal = () => {
  const { dur } = BEATS.reveal;
  const out = useOut(dur);
  return (
    <AbsoluteFill style={{ opacity: out }}>
      <MapClip startFrom={0} dur={dur} />
      <Vignette />
      <AbsoluteFill style={{ padding: "120px 130px", justifyContent: "flex-end" }}>
        <Rise delay={20}>
          <Kicker>CareGist</Kicker>
        </Rise>
        <Rise delay={32}>
          <div style={{ fontFamily: SERIF, fontWeight: 700, fontSize: 84, color: C.parchment, lineHeight: 1.05, maxWidth: 900, marginTop: 18 }}>
            Every registered care location in England.
          </div>
        </Rise>
        <Rise delay={56}>
          <div style={{ fontFamily: SANS, fontSize: 32, color: "rgba(245,239,228,0.75)", marginTop: 22 }}>
            55,000+ services on the public CQC register. Mapped.
          </div>
        </Rise>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/* ---------- 2. Question ---------- */
const Question = () => {
  const { dur } = BEATS.question;
  const out = useOut(dur);
  const lines = [
    { t: "You sell into care.", d: 4, c: C.parchment },
    { t: "What changed in your region this week?", d: 34, c: C.amber },
    { t: "And where should you start?", d: 68, c: C.clay },
  ];
  return (
    <AbsoluteFill style={{ background: C.charcoal, opacity: out }}>
      {QUESTION_BROLL ? (
        <>
          {/* Soft focus keeps the laptop's generated map (not a real England outline) from reading. */}
          <AbsoluteFill style={{ opacity: 0.6, filter: "blur(5px) saturate(0.9)", transform: "scale(1.04)" }}>
            <OffthreadVideo src={staticFile(QUESTION_BROLL)} muted />
          </AbsoluteFill>
          <AbsoluteFill
            style={{ background: "linear-gradient(90deg, rgba(43,37,32,0.92) 0%, rgba(43,37,32,0.7) 45%, rgba(43,37,32,0.35) 100%)" }}
          />
        </>
      ) : null}
      <AbsoluteFill style={{ justifyContent: "center", padding: "0 160px", gap: 18 }}>
        {lines.map((l) => (
          <Rise key={l.t} delay={l.d} y={40}>
            <div style={{ fontFamily: SERIF, fontWeight: 700, fontSize: 76, color: l.c, lineHeight: 1.1 }}>{l.t}</div>
          </Rise>
        ))}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/* ---------- product badge used over the map beats ---------- */
const ProductBadge: React.FC<{ step: string; name: string; line: string; color: string }> = ({ step, name, line, color }) => (
  <div style={{ position: "absolute", left: 120, top: 110 }}>
    <Rise delay={8}>
      <Kicker color={color}>{step}</Kicker>
    </Rise>
    <Rise delay={16}>
      <div style={{ fontFamily: SERIF, fontWeight: 800, fontSize: 92, color: C.parchment, marginTop: 10 }}>{name}</div>
    </Rise>
    <Rise delay={28}>
      <div style={{ fontFamily: SANS, fontSize: 34, color: "rgba(245,239,228,0.8)", marginTop: 8 }}>{line}</div>
    </Rise>
  </div>
);

const Dot: React.FC<{ color: string }> = ({ color }) => (
  <span style={{ display: "inline-block", width: 16, height: 16, borderRadius: 8, background: color, boxShadow: `0 0 18px ${color}` }} />
);

/* ---------- 3. Digest on the map ---------- */
const DigestMap = () => {
  const { dur, map } = BEATS.digestMap;
  const out = useOut(dur);
  return (
    <AbsoluteFill style={{ opacity: out }}>
      <MapClip startFrom={map} dur={dur} />
      <Vignette />
      <ProductBadge step="Step one" name="Weekly Digest" line="See what changed in one region." color={C.amber} />
      <div style={{ position: "absolute", left: 120, bottom: 100, display: "flex", gap: 40, alignItems: "center" }}>
        <Rise delay={40} style={{ display: "flex", gap: 14, alignItems: "center" }}>
          <Dot color={C.amber} />
          <span style={{ fontFamily: SANS, fontSize: 26, color: C.parchment }}>New registrations</span>
        </Rise>
        <Rise delay={52} style={{ display: "flex", gap: 14, alignItems: "center" }}>
          <Dot color={C.sage} />
          <span style={{ fontFamily: SANS, fontSize: 26, color: C.parchment }}>Rating changes</span>
        </Rise>
        <Rise delay={64}>
          <Fine>West Midlands shown · illustrative signals</Fine>
        </Rise>
      </div>
    </AbsoluteFill>
  );
};

/* ---------- 4. Digest product UI ---------- */
type Row = { tag: "New registration" | "Rating change"; name: string; place: string; detail: string };
const ISSUES: Row[][] = [
  [
    { tag: "New registration", name: "Example Homecare Ltd", place: "Wolverhampton", detail: "Domiciliary care" },
    { tag: "Rating change", name: "Sample Lodge Care Home", place: "Worcester", detail: "Requires improvement → Good" },
    { tag: "New registration", name: "Illustrative Support Services", place: "Coventry", detail: "Supported living" },
  ],
  [
    { tag: "Rating change", name: "Demo House Nursing Home", place: "Stoke-on-Trent", detail: "Good → Requires improvement" },
    { tag: "New registration", name: "Placeholder Care Group", place: "Telford", detail: "Domiciliary care" },
    { tag: "New registration", name: "Fictional Lane Care", place: "Hereford", detail: "Residential care" },
  ],
  [
    { tag: "New registration", name: "Sample Community Care", place: "Birmingham", detail: "Domiciliary care" },
    { tag: "Rating change", name: "Example Court", place: "Walsall", detail: "Inadequate → Requires improvement" },
    { tag: "New registration", name: "Mock Meadows Living", place: "Shrewsbury", detail: "Supported living" },
  ],
  [
    { tag: "Rating change", name: "Illustrative Grange", place: "Dudley", detail: "Requires improvement → Good" },
    { tag: "New registration", name: "Test Street Homecare", place: "Solihull", detail: "Domiciliary care" },
    { tag: "New registration", name: "Demo Valley Care", place: "Nuneaton", detail: "Residential care" },
  ],
];

const DigestCard = () => {
  const f = useCurrentFrame();
  const perIssue = 72;
  const start = 40;
  const issue = Math.min(3, Math.max(0, Math.floor((f - start) / perIssue)));
  const local = f - start - issue * perIssue;
  const cardIn = useIn(10, 30);
  return (
    <div
      style={{
        width: 820,
        background: C.cream,
        borderRadius: 28,
        boxShadow: "0 40px 120px rgba(0,0,0,0.45)",
        padding: "40px 44px",
        opacity: cardIn,
        transform: `translateY(${(1 - cardIn) * 60}px) rotate(${(1 - cardIn) * -2}deg)`,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ fontFamily: SERIF, fontWeight: 700, fontSize: 36, color: C.bark }}>Weekly Digest · West Midlands</div>
        <div style={{ display: "flex", gap: 10 }}>
          {[0, 1, 2, 3].map((i) => (
            <div
              key={i}
              style={{
                width: 46,
                height: 46,
                borderRadius: 23,
                display: "grid",
                placeItems: "center",
                fontFamily: SANS,
                fontWeight: 600,
                fontSize: 20,
                color: i <= issue ? C.cream : C.dusk,
                background: i <= issue ? C.amber : "transparent",
                border: `2px solid ${i <= issue ? C.amber : C.stone}`,
              }}
            >
              {i + 1}
            </div>
          ))}
        </div>
      </div>
      <div style={{ fontFamily: SANS, fontSize: 20, color: C.dusk, marginTop: 6 }}>
        Issue {issue + 1} of 4 · each row links to its CQC source and date
      </div>
      <div style={{ marginTop: 26, display: "flex", flexDirection: "column", gap: 14 }}>
        {ISSUES[issue].map((r, i) => {
          const p = interpolate(local - i * 8, [0, 16], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ease });
          const isNew = r.tag === "New registration";
          return (
            <div
              key={r.name}
              style={{
                opacity: p,
                transform: `translateX(${(1 - p) * 40}px)`,
                display: "flex",
                alignItems: "center",
                gap: 18,
                padding: "18px 22px",
                borderRadius: 16,
                background: C.parchment,
                border: `1px solid ${C.stone}`,
              }}
            >
              <div
                style={{
                  fontFamily: SANS,
                  fontWeight: 600,
                  fontSize: 16,
                  letterSpacing: 1.2,
                  textTransform: "uppercase",
                  color: C.cream,
                  background: isNew ? C.amber : C.moss,
                  padding: "6px 12px",
                  borderRadius: 8,
                  whiteSpace: "nowrap",
                }}
              >
                {r.tag}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontFamily: SANS, fontWeight: 600, fontSize: 24, color: C.charcoal }}>{r.name}</div>
                <div style={{ fontFamily: SANS, fontSize: 19, color: C.dusk }}>
                  {r.place} · {r.detail}
                </div>
              </div>
            </div>
          );
        })}
      </div>
      <div style={{ fontFamily: SANS, fontSize: 16, color: C.dusk, marginTop: 20, fontStyle: "italic" }}>
        Illustrative sample. Names are fictional, not live data.
      </div>
    </div>
  );
};

const FactList: React.FC<{ items: string[]; start: number; color: string }> = ({ items, start, color }) => (
  <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>
    {items.map((t, i) => (
      <Rise key={t} delay={start + i * 14}>
        <div style={{ display: "flex", gap: 18, alignItems: "baseline" }}>
          <span style={{ width: 12, height: 12, borderRadius: 6, background: color, flexShrink: 0, transform: "translateY(-4px)" }} />
          <span style={{ fontFamily: SANS, fontSize: 34, color: C.parchment, lineHeight: 1.25 }}>{t}</span>
        </div>
      </Rise>
    ))}
  </div>
);

const Price: React.FC<{ amount: string; note: string; delay: number; color: string }> = ({ amount, note, delay, color }) => (
  <Rise delay={delay} style={{ marginTop: 44, display: "flex", alignItems: "baseline", gap: 18 }}>
    <span style={{ fontFamily: SERIF, fontWeight: 800, fontSize: 84, color }}>{amount}</span>
    <span style={{ fontFamily: SANS, fontSize: 28, color: "rgba(245,239,228,0.75)" }}>{note}</span>
  </Rise>
);

const DigestUi = () => {
  const { dur } = BEATS.digestUi;
  const out = useOut(dur);
  return (
    <AbsoluteFill style={{ background: `linear-gradient(135deg, ${C.charcoal} 0%, #3a2e25 100%)`, opacity: out }}>
      <AbsoluteFill style={{ flexDirection: "row", alignItems: "center", padding: "0 120px", gap: 90 }}>
        <div style={{ flex: 1 }}>
          <Rise>
            <Kicker>Weekly Digest</Kicker>
          </Rise>
          <Rise delay={8}>
            <div style={{ fontFamily: SERIF, fontWeight: 700, fontSize: 64, color: C.parchment, lineHeight: 1.1, margin: "16px 0 40px" }}>
              Keep track of public changes, week by week.
            </div>
          </Rise>
          <FactList
            color={C.amber}
            start={30}
            items={["One England region", "Four weekly digests", "New registrations and rating changes", "Source dates on every row"]}
          />
          <Price amount="£150" note="once · no automatic renewal" delay={110} color={C.amber} />
        </div>
        <DigestCard />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/* ---------- 5. Bridge ---------- */
const Pill: React.FC<{ label: string; color: string; x: number; opacity?: number }> = ({ label, color, x, opacity = 1 }) => (
  <div
    style={{
      position: "absolute",
      left: "50%",
      top: "58%",
      transform: `translate(calc(-50% + ${x}px), -50%)`,
      opacity,
      fontFamily: SANS,
      fontWeight: 600,
      fontSize: 32,
      color: C.cream,
      background: color,
      padding: "20px 38px",
      borderRadius: 999,
      whiteSpace: "nowrap",
      boxShadow: `0 0 60px ${color}66`,
    }}
  >
    {label}
  </div>
);

const Bridge = () => {
  const f = useCurrentFrame();
  const { dur } = BEATS.bridge;
  const out = useOut(dur);
  const slide = interpolate(f, [26, 62], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ease });
  const arrow = interpolate(f, [30, 60], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ease });
  return (
    <AbsoluteFill style={{ background: C.charcoal, opacity: out }}>
      <AbsoluteFill style={{ alignItems: "center", paddingTop: 230 }}>
        <Rise delay={2}>
          <div style={{ fontFamily: SERIF, fontWeight: 700, fontSize: 72, color: C.parchment, textAlign: "center" }}>
            Seen movement in your region?
          </div>
        </Rise>
        <Rise delay={22}>
          <div style={{ fontFamily: SERIF, fontWeight: 700, fontSize: 72, color: C.clay, textAlign: "center", marginTop: 6 }}>
            Decide where to start.
          </div>
        </Rise>
      </AbsoluteFill>
      <Pill label="Weekly Digest" color={C.amber} x={-260 * slide} />
      <div
        style={{
          position: "absolute",
          left: "50%",
          top: "58%",
          width: 150 * arrow,
          height: 4,
          background: C.parchment,
          transform: "translate(-50%, -50%)",
          opacity: arrow,
        }}
      />
      <Pill label="Territory Brief" color={C.clay} x={260 * slide} opacity={slide} />
    </AbsoluteFill>
  );
};

/* ---------- 6. Brief on the map ---------- */
const BriefMap = () => {
  const { dur, map } = BEATS.briefMap;
  const out = useOut(dur);
  return (
    <AbsoluteFill style={{ opacity: out }}>
      <MapClip startFrom={map} dur={dur} />
      <Vignette />
      <ProductBadge step="Step two" name="Territory Opportunity Brief" line="Decide which accounts to investigate." color={C.clay} />
      <div style={{ position: "absolute", left: 120, bottom: 100 }}>
        <Rise delay={70}>
          <div style={{ display: "flex", gap: 14, alignItems: "center" }}>
            <Dot color={C.clay} />
            <span style={{ fontFamily: SANS, fontSize: 26, color: C.parchment }}>A shortlist of 25–50 provider organisations</span>
          </div>
        </Rise>
        <Rise delay={84}>
          <Fine style={{ marginTop: 10 }}>Illustrative shortlist</Fine>
        </Rise>
      </div>
    </AbsoluteFill>
  );
};

/* ---------- 7. Brief product UI ---------- */
const FileCard: React.FC<{ ext: string; name: string; line: string; delay: number; color: string; tilt: number }> = ({
  ext,
  name,
  line,
  delay,
  color,
  tilt,
}) => {
  const { fps } = useVideoConfig();
  const f = useCurrentFrame();
  const s = spring({ frame: f - delay, fps, config: { damping: 16, mass: 0.8 } });
  return (
    <div
      style={{
        width: 300,
        height: 380,
        background: C.cream,
        borderRadius: 22,
        padding: 30,
        boxShadow: "0 30px 90px rgba(0,0,0,0.45)",
        transform: `translateY(${(1 - s) * 220}px) rotate(${tilt * s}deg)`,
        opacity: Math.min(1, s * 1.4),
        display: "flex",
        flexDirection: "column",
      }}
    >
      <div
        style={{
          alignSelf: "flex-start",
          fontFamily: SANS,
          fontWeight: 600,
          fontSize: 22,
          letterSpacing: 2,
          color: C.cream,
          background: color,
          padding: "8px 16px",
          borderRadius: 10,
        }}
      >
        {ext}
      </div>
      <div style={{ marginTop: 26, display: "flex", flexDirection: "column", gap: 10 }}>
        {[0.95, 0.8, 0.88, 0.6, 0.75].map((w, i) => (
          <div key={i} style={{ height: 10, width: `${w * 100}%`, borderRadius: 5, background: C.stone }} />
        ))}
      </div>
      <div style={{ marginTop: "auto" }}>
        <div style={{ fontFamily: SANS, fontWeight: 600, fontSize: 24, color: C.charcoal }}>{name}</div>
        <div style={{ fontFamily: SANS, fontSize: 18, color: C.dusk, marginTop: 6, lineHeight: 1.35 }}>{line}</div>
      </div>
    </div>
  );
};

const BriefUi = () => {
  const { dur } = BEATS.briefUi;
  const out = useOut(dur);
  return (
    <AbsoluteFill style={{ background: `linear-gradient(135deg, ${C.charcoal} 0%, #3b2a22 100%)`, opacity: out }}>
      <AbsoluteFill style={{ flexDirection: "row", alignItems: "center", padding: "0 120px", gap: 70 }}>
        <div style={{ flex: 1 }}>
          <Rise>
            <Kicker color={C.clay}>Territory Opportunity Brief</Kicker>
          </Rise>
          <Rise delay={8}>
            <div style={{ fontFamily: SERIF, fontWeight: 700, fontSize: 64, color: C.parchment, lineHeight: 1.1, margin: "16px 0 40px" }}>
              Your territory, turned into a shortlist.
            </div>
          </Rise>
          <FactList
            color={C.clay}
            start={30}
            items={["Agreed territory and scope", "25–50 distinct provider organisations", "Why each one is included, with sources", "PDF, CSV and source manifest"]}
          />
          <Price amount="£745" note="once · fixed fee" delay={110} color={C.clay} />
        </div>
        <div style={{ display: "flex", gap: 26, alignItems: "flex-end" }}>
          <FileCard ext="PDF" name="Territory brief" line="Scope, method, limitations and the shortlist" delay={40} color={C.clay} tilt={-4} />
          <FileCard ext="CSV" name="Shortlist" line="Provider and location IDs, ready for your CRM" delay={56} color={C.moss} tilt={1} />
          <FileCard ext="MD" name="Source manifest" line="Sources, check dates and licence" delay={72} color={C.bark} tilt={5} />
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/* ---------- 8. The loop ---------- */
const Loop = () => {
  const f = useCurrentFrame();
  const { dur } = BEATS.loop;
  const out = useOut(dur);
  const cx = 960;
  const cy = 600;
  const r = 250;
  const draw = interpolate(f, [10, 70], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ease });
  const circ = 2 * Math.PI * r;
  const travel = ((f - 40) / 90) * 2 * Math.PI - Math.PI / 2;
  const dotOn = f > 60 ? 1 : 0;
  const node = (label: string, sub: string, x: number, y: number, color: string, delay: number) => (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        transform: "translate(-50%, -50%)",
        textAlign: "center",
      }}
    >
      <Rise delay={delay}>
        <div
          style={{
            fontFamily: SANS,
            fontWeight: 600,
            fontSize: 34,
            color: C.cream,
            background: color,
            padding: "22px 40px",
            borderRadius: 999,
            boxShadow: `0 0 70px ${color}77`,
            whiteSpace: "nowrap",
          }}
        >
          {label}
        </div>
        <div
          style={{
            fontFamily: SANS,
            fontSize: 24,
            color: "rgba(245,239,228,0.8)",
            marginTop: 14,
            background: C.charcoal,
            padding: "4px 12px",
            display: "inline-block",
          }}
        >
          {sub}
        </div>
      </Rise>
    </div>
  );
  return (
    <AbsoluteFill style={{ background: C.charcoal, opacity: out }}>
      <AbsoluteFill style={{ alignItems: "center", paddingTop: 90 }}>
        <Rise>
          <div style={{ fontFamily: SERIF, fontWeight: 700, fontSize: 76, color: C.parchment }}>Each one leads to the next.</div>
        </Rise>
      </AbsoluteFill>
      <svg width={1920} height={1080} style={{ position: "absolute" }}>
        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke="rgba(245,239,228,0.35)"
          strokeWidth={4}
          strokeDasharray={circ}
          strokeDashoffset={circ * (1 - draw)}
          transform={`rotate(-90 ${cx} ${cy})`}
        />
        <circle cx={cx + r * Math.cos(travel)} cy={cy + r * Math.sin(travel)} r={12} fill={C.parchment} opacity={dotOn} />
      </svg>
      {node("Weekly Digest", "spot what changed", cx - r, cy, C.amber, 20)}
      {node("Territory Brief", "decide where to start", cx + r, cy, C.clay, 34)}
      <div style={{ position: "absolute", left: cx, top: cy - r - 52, transform: "translateX(-50%)" }}>
        <Rise delay={70}>
          <Fine color={C.parchment} style={{ fontSize: 24 }}>movement → shortlist</Fine>
        </Rise>
      </div>
      <div style={{ position: "absolute", left: cx, top: cy + r + 26, transform: "translateX(-50%)" }}>
        <Rise delay={90}>
          <Fine color={C.parchment} style={{ fontSize: 24 }}>shortlist → stay current</Fine>
        </Rise>
      </div>
    </AbsoluteFill>
  );
};

/* ---------- 9. Call to action ---------- */
const Cta = () => {
  const f = useCurrentFrame();
  const arcLen = 330;
  const draw = interpolate(f, [6, 50], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ease });
  const signal = interpolate(f, [40, 62], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ease });
  const fadeOut = interpolate(f, [BEATS.cta.dur - 20, BEATS.cta.dur], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ background: C.parchment, alignItems: "center", justifyContent: "center", opacity: fadeOut }}>
      <div style={{ display: "flex", alignItems: "center", gap: 36 }}>
        <svg viewBox="0 0 180 180" width={200} height={200}>
          <path
            d="M134 34 A68 68 0 1 0 134 146"
            fill="none"
            stroke={C.bark}
            strokeWidth={22}
            strokeLinecap="round"
            strokeDasharray={arcLen}
            strokeDashoffset={arcLen * (1 - draw)}
          />
          <path d="M100 90 H126" fill="none" stroke={C.clay} strokeWidth={18} strokeLinecap="round" opacity={signal} />
          <circle cx={132} cy={90} r={11 * signal} fill={C.clay} />
        </svg>
        <Rise delay={30} y={20}>
          <div style={{ fontFamily: SERIF, fontWeight: 700, fontSize: 130, color: C.bark, letterSpacing: -3 }}>CareGist</div>
        </Rise>
      </div>
      <Rise delay={60}>
        <div style={{ fontFamily: SERIF, fontWeight: 700, fontSize: 56, color: C.charcoal, marginTop: 30 }}>
          Start with the region you know.
        </div>
      </Rise>
      <Rise delay={78}>
        <div style={{ fontFamily: SANS, fontWeight: 600, fontSize: 38, color: C.cta, marginTop: 26 }}>caregist.co.uk</div>
      </Rise>
      <div style={{ position: "absolute", bottom: 56, left: 0, right: 0, textAlign: "center" }}>
        <Rise delay={96}>
          <Fine color={C.dusk} style={{ fontSize: 19, lineHeight: 1.5 }}>
            CareGist is independent of CQC and built from public CQC records. Shortlists are organisations to investigate,
            <br />
            not leads ready to buy. Published fees, no VAT charged; terms confirmed before any order.
          </Fine>
        </Rise>
      </div>
    </AbsoluteFill>
  );
};

export const Launch = () => (
  <AbsoluteFill style={{ background: C.charcoal }}>
    <style>{fontFaces}</style>
    <Audio src={staticFile("score.wav")} />
    <Sequence from={BEATS.reveal.from} durationInFrames={BEATS.reveal.dur}>
      <Reveal />
    </Sequence>
    <Sequence from={BEATS.question.from} durationInFrames={BEATS.question.dur}>
      <Question />
    </Sequence>
    <Sequence from={BEATS.digestMap.from} durationInFrames={BEATS.digestMap.dur}>
      <DigestMap />
    </Sequence>
    <Sequence from={BEATS.digestUi.from} durationInFrames={BEATS.digestUi.dur}>
      <DigestUi />
    </Sequence>
    <Sequence from={BEATS.bridge.from} durationInFrames={BEATS.bridge.dur}>
      <Bridge />
    </Sequence>
    <Sequence from={BEATS.briefMap.from} durationInFrames={BEATS.briefMap.dur}>
      <BriefMap />
    </Sequence>
    <Sequence from={BEATS.briefUi.from} durationInFrames={BEATS.briefUi.dur}>
      <BriefUi />
    </Sequence>
    <Sequence from={BEATS.loop.from} durationInFrames={BEATS.loop.dur}>
      <Loop />
    </Sequence>
    <Sequence from={BEATS.cta.from} durationInFrames={BEATS.cta.dur}>
      <Cta />
    </Sequence>
  </AbsoluteFill>
);
