"use client";

import { useEffect, useMemo, useRef, useState } from "react";

type StoryScene = {
  id: string;
  title: string;
  duration: number;
  palette: {
    skyTop: string;
    skyBottom: string;
    ground: string;
    accent: string;
    card: string;
  };
  mode: "chaos" | "lesson" | "home" | "school" | "dinner" | "montage" | "finale";
  narration: string;
  beats: string[];
};

const scenes: StoryScene[] = [
  {
    id: "chaos",
    title: "A Very Noisy House",
    duration: 25,
    palette: {
      skyTop: "#f8d8a7",
      skyBottom: "#f1a66a",
      ground: "#d58059",
      accent: "#c44444",
      card: "rgba(107, 76, 53, 0.82)",
    },
    mode: "chaos",
    narration:
      "Crash. Bang. Stomp. This was not a quiet house. Anna shouted, Ben refused to help, and Caleb yelled when things felt unfair. Then, on one very strange morning, the whole house groaned as if it were tired of all the arguing.",
    beats: [
      "Crash! Bang! Stomp!",
      "Anna: Mine!",
      "Ben: I am not cleaning that up!",
      "Caleb: It is not fair!",
      "The house groans...",
    ],
  },
  {
    id: "parents",
    title: "The House Feels Unhappy",
    duration: 20,
    palette: {
      skyTop: "#f8ddb4",
      skyBottom: "#f7c98b",
      ground: "#93aa6f",
      accent: "#6b4c35",
      card: "rgba(74, 94, 69, 0.82)",
    },
    mode: "home",
    narration:
      "Mother looked at the wobbling lamp and the rattling door. She told the children that their home did not feel peaceful at all. Father promised that tomorrow they would learn something important.",
    beats: [
      "Mother sees the mess",
      "The lamp wiggles",
      "The children stare",
      "Father has an idea",
    ],
  },
  {
    id: "sticks",
    title: "The Three Sticks",
    duration: 30,
    palette: {
      skyTop: "#9fd1ff",
      skyBottom: "#d8efff",
      ground: "#82b46a",
      accent: "#d4943a",
      card: "rgba(43, 37, 32, 0.82)",
    },
    mode: "lesson",
    narration:
      "The next morning, Father gave each child a stick. Snap, snap, snap. They all broke easily. Then he tied three sticks together. The children pushed and strained, but the bundle would not break. Father smiled and said, together is stronger.",
    beats: [
      "One stick each",
      "Snap! Snap! Snap!",
      "Now the bundle",
      "Push! Huff! Oof!",
      "Stronger together",
    ],
  },
  {
    id: "anna",
    title: "Anna Chooses Kindness",
    duration: 35,
    palette: {
      skyTop: "#fce7b8",
      skyBottom: "#f9d886",
      ground: "#8abb73",
      accent: "#bc6c25",
      card: "rgba(107, 76, 53, 0.82)",
    },
    mode: "home",
    narration:
      "That afternoon, Anna built a tall block castle. Caleb bumped it by accident, and it came tumbling down. Anna felt a shout rising inside her, but she remembered the sticks. She took a breath and asked Caleb to help her build it again. Together they built an even better castle.",
    beats: [
      "Anna builds a castle",
      "Caleb bumps it",
      "Crash! Blocks tumble",
      "Anna takes a breath",
      "They rebuild together",
    ],
  },
  {
    id: "sigh",
    title: "The House Breathes Out",
    duration: 20,
    palette: {
      skyTop: "#ffdca2",
      skyBottom: "#ffc46e",
      ground: "#92b781",
      accent: "#4a5e45",
      card: "rgba(74, 94, 69, 0.82)",
    },
    mode: "home",
    narration:
      "That evening, the house made a new sound. Not a groan this time, but a soft and relieved sigh. Ben heard it and looked around in wonder.",
    beats: [
      "Quiet evening",
      "Soft happy sigh",
      "Ben hears it",
      "The house feels lighter",
    ],
  },
  {
    id: "ben",
    title: "Ben Helps First",
    duration: 30,
    palette: {
      skyTop: "#d8edff",
      skyBottom: "#b8ddff",
      ground: "#94be6a",
      accent: "#3d6f9c",
      card: "rgba(61, 111, 156, 0.82)",
    },
    mode: "school",
    narration:
      "At school, Ben saw paper scraps and crayons all over the floor after art time. He almost walked away. Then he remembered: stronger together. Ben picked up one paper, then another, and soon his classmates joined in. Their teacher smiled at his kindness.",
    beats: [
      "Art class is messy",
      "Ben almost walks away",
      "He remembers the sticks",
      "Friends join in",
      "Teacher smiles",
    ],
  },
  {
    id: "caleb",
    title: "Caleb Uses Calm Words",
    duration: 30,
    palette: {
      skyTop: "#fde2d0",
      skyBottom: "#f6bf9d",
      ground: "#9fbb78",
      accent: "#275d63",
      card: "rgba(39, 93, 99, 0.82)",
    },
    mode: "dinner",
    narration:
      "At dinner, Anna got the blue cup that Caleb wanted. His eyebrows squeezed, and a loud yell almost burst out. But Caleb stopped, breathed in, and asked politely if he could have the blue cup tomorrow. Anna said yes. Mother called that kindness, and Father called that strength.",
    beats: [
      "The blue cup appears",
      "Caleb feels upset",
      "He takes a breath",
      "Can I have it tomorrow?",
      "The lamp does a happy jiggle",
    ],
  },
  {
    id: "montage",
    title: "Practice Every Day",
    duration: 40,
    palette: {
      skyTop: "#daf7ef",
      skyBottom: "#bae7cf",
      ground: "#89b96f",
      accent: "#4a5e45",
      card: "rgba(74, 94, 69, 0.82)",
    },
    mode: "montage",
    narration:
      "After that, the children kept practicing. Anna shared her crayons. Ben carried groceries. Caleb used kind words when he felt upset. They cleaned together, played together, and laughed together. The more they worked together, the brighter the whole house seemed to shine.",
    beats: [
      "Share toys",
      "Carry groceries",
      "Kind words",
      "Clean together",
      "Laugh together",
    ],
  },
  {
    id: "message",
    title: "What God Wants For Us",
    duration: 35,
    palette: {
      skyTop: "#fff0c2",
      skyBottom: "#ffe08e",
      ground: "#7da164",
      accent: "#8b5e34",
      card: "rgba(107, 76, 53, 0.82)",
    },
    mode: "home",
    narration:
      "Mother watched her children helping one another and smiled. She said this is what God wants for us: a home filled with love, kindness, and peace. Father held up the bundle of sticks, and the children remembered what they had learned.",
    beats: [
      "Mother smiles",
      "A peaceful home",
      "Father lifts the sticks",
      "The lesson returns",
      "Love, kindness, peace",
    ],
  },
  {
    id: "finale",
    title: "Together Is Better",
    duration: 35,
    palette: {
      skyTop: "#8cc9ff",
      skyBottom: "#f7f0bb",
      ground: "#6b9656",
      accent: "#d4943a",
      card: "rgba(43, 37, 32, 0.82)",
    },
    mode: "finale",
    narration:
      "From that day on, the house was still full of noise, but now it was the best kind of noise: giggles, kind voices, clinking dishes, and happy feet. And if you listened very closely on peaceful evenings, you could hear the house humming happily too. Love one another. Help each other. Speak kindly. Work together.",
    beats: [
      "Giggles and music",
      "Kind voices",
      "Happy humming house",
      "Love one another",
      "Work together",
    ],
  },
];

const totalDuration = scenes.reduce((sum, scene) => sum + scene.duration, 0);

function formatTime(totalSeconds: number) {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}

function Character({
  name,
  color,
  x,
  y,
  active,
  bounce,
}: {
  name: string;
  color: string;
  x: string;
  y: string;
  active?: boolean;
  bounce?: boolean;
}) {
  return (
    <div
      className={`absolute transition-all duration-700 ${bounce ? "animate-[float_2.2s_ease-in-out_infinite]" : ""}`}
      style={{ left: x, bottom: y }}
    >
      <div className={`relative ${active ? "scale-105" : "scale-100"} transition-transform duration-500`}>
        <div className="mx-auto h-12 w-12 rounded-full border-4 border-white/70" style={{ backgroundColor: color }} />
        <div className="mx-auto -mt-1 h-16 w-14 rounded-t-[1.4rem] rounded-b-xl border-4 border-white/70 bg-white/85" />
        <div className="mt-2 text-center text-xs font-semibold text-white drop-shadow-[0_1px_0_rgba(0,0,0,0.45)]">
          {name}
        </div>
      </div>
    </div>
  );
}

function House({ mode }: { mode: StoryScene["mode"] }) {
  const animatedClass =
    mode === "chaos" ? "animate-[houseShake_0.7s_ease-in-out_infinite]" : mode === "finale" ? "animate-[houseHum_2.4s_ease-in-out_infinite]" : "";

  return (
    <div className={`absolute left-1/2 top-[42%] h-64 w-72 -translate-x-1/2 -translate-y-1/2 ${animatedClass}`}>
      <div className="absolute inset-x-8 top-10 h-40 rounded-[2rem] border-4 border-bark bg-parchment shadow-[0_16px_0_rgba(107,76,53,0.12)]" />
      <div className="absolute left-8 top-0 h-24 w-28 -skew-x-12 rounded-tl-[3rem] border-4 border-bark bg-clay" />
      <div className="absolute right-8 top-0 h-24 w-28 skew-x-12 rounded-tr-[3rem] border-4 border-bark bg-clay" />
      <div className={`absolute left-[4.7rem] top-[6.4rem] h-12 w-12 rounded-xl border-4 border-bark ${mode === "chaos" ? "bg-alert" : "bg-amber"}`} />
      <div className={`absolute right-[4.7rem] top-[6.4rem] h-12 w-12 rounded-xl border-4 border-bark ${mode === "chaos" ? "bg-alert" : "bg-amber"}`} />
      <div className="absolute left-1/2 top-[7rem] h-20 w-14 -translate-x-1/2 rounded-t-2xl border-4 border-bark bg-sage" />
      <div className="absolute left-[2.4rem] top-[9.9rem] h-3 w-4 rounded-full bg-bark/70" />
      <div className="absolute right-[2.4rem] top-[9.9rem] h-3 w-4 rounded-full bg-bark/70" />
    </div>
  );
}

export default function StoryVideoPlayer() {
  const [elapsed, setElapsed] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [speechOn, setSpeechOn] = useState(true);
  const [hasStarted, setHasStarted] = useState(false);
  const speechRef = useRef<number | null>(null);
  const spokenSceneRef = useRef<string | null>(null);

  const timeline = useMemo(() => {
    let cursor = 0;
    return scenes.map((scene) => {
      const start = cursor;
      cursor += scene.duration;
      return { ...scene, start, end: cursor };
    });
  }, []);

  const activeScene =
    timeline.find((scene) => elapsed >= scene.start && elapsed < scene.end) ?? timeline[timeline.length - 1];
  const localElapsed = Math.max(0, elapsed - activeScene.start);
  const beatLength = activeScene.duration / activeScene.beats.length;
  const beatIndex = Math.min(activeScene.beats.length - 1, Math.floor(localElapsed / beatLength));
  const progress = Math.min(100, (elapsed / totalDuration) * 100);

  useEffect(() => {
    if (!isPlaying) return;

    speechRef.current = window.setInterval(() => {
      setElapsed((current) => {
        if (current >= totalDuration) {
          window.clearInterval(speechRef.current ?? undefined);
          return totalDuration;
        }
        return Math.min(totalDuration, current + 1);
      });
    }, 1000);

    return () => {
      if (speechRef.current) {
        window.clearInterval(speechRef.current);
      }
    };
  }, [isPlaying]);

  useEffect(() => {
    if (elapsed >= totalDuration) {
      setIsPlaying(false);
      if ("speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
    }
  }, [elapsed]);

  useEffect(() => {
    if (!speechOn || !isPlaying || !hasStarted) return;
    if (!("speechSynthesis" in window)) return;
    if (spokenSceneRef.current === activeScene.id) return;

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(activeScene.narration);
    utterance.rate = 0.92;
    utterance.pitch = 1.03;
    utterance.volume = 1;
    spokenSceneRef.current = activeScene.id;
    window.speechSynthesis.speak(utterance);
  }, [activeScene, hasStarted, isPlaying, speechOn]);

  useEffect(() => {
    if (speechOn) return;
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
  }, [speechOn]);

  useEffect(() => {
    return () => {
      if ("speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  function startPlayback() {
    setHasStarted(true);
    if (elapsed >= totalDuration) {
      spokenSceneRef.current = null;
      setElapsed(0);
    }
    setIsPlaying(true);
  }

  function pausePlayback() {
    setIsPlaying(false);
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
    spokenSceneRef.current = null;
  }

  function replayPlayback() {
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
    spokenSceneRef.current = null;
    setElapsed(0);
    setHasStarted(true);
    setIsPlaying(true);
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,#fff8e8_0%,#f5efe4_44%,#eedbc4_100%)] px-4 py-8 md:px-6 md:py-10">
      <div className="mx-auto max-w-6xl">
        <section className="mb-6 rounded-[2rem] border border-bark/10 bg-white/70 p-6 shadow-[0_24px_60px_rgba(107,76,53,0.12)] backdrop-blur">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-3xl">
              <p className="mb-3 text-xs font-semibold uppercase tracking-[0.26em] text-clay">
                Animated Story Experience
              </p>
              <h1 className="mb-3 text-4xl font-black text-bark md:text-6xl">The House That Worked Together</h1>
              <p className="max-w-2xl text-base leading-7 text-charcoal/80 md:text-lg">
                A self-contained five-minute animated story with scene timing, captions, motion, and optional browser narration.
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <button
                type="button"
                onClick={isPlaying ? pausePlayback : startPlayback}
                className="rounded-full bg-bark px-5 py-3 text-sm font-semibold text-cream transition hover:bg-charcoal"
              >
                {isPlaying ? "Pause story" : hasStarted ? "Resume story" : "Start story"}
              </button>
              <button
                type="button"
                onClick={replayPlayback}
                className="rounded-full border border-bark/15 bg-white px-5 py-3 text-sm font-semibold text-bark transition hover:border-bark/30 hover:bg-parchment"
              >
                Replay from start
              </button>
              <button
                type="button"
                onClick={() => setSpeechOn((current) => !current)}
                className="rounded-full border border-bark/15 bg-white px-5 py-3 text-sm font-semibold text-bark transition hover:border-bark/30 hover:bg-parchment"
              >
                {speechOn ? "Narration on" : "Narration off"}
              </button>
            </div>
          </div>

          <div className="mt-6 grid gap-4 lg:grid-cols-[1.4fr_0.6fr]">
            <div>
              <div className="mb-2 flex items-center justify-between text-sm font-medium text-bark/70">
                <span>{activeScene.title}</span>
                <span>
                  {formatTime(elapsed)} / {formatTime(totalDuration)}
                </span>
              </div>
              <div className="h-3 overflow-hidden rounded-full bg-bark/10">
                <div
                  className="h-full rounded-full bg-[linear-gradient(90deg,#c1784f_0%,#d4943a_60%,#7e9b79_100%)] transition-all duration-700"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
            <div className="rounded-3xl border border-bark/10 bg-white/80 px-4 py-3 text-sm text-charcoal/75">
              Best experience: press `Start story`, then use browser fullscreen.
            </div>
          </div>
        </section>

        <section className="grid gap-6 lg:grid-cols-[1.55fr_0.85fr]">
          <div
            className="relative overflow-hidden rounded-[2rem] border border-bark/10 shadow-[0_26px_60px_rgba(43,37,32,0.18)]"
            style={{
              background: `linear-gradient(180deg, ${activeScene.palette.skyTop} 0%, ${activeScene.palette.skyBottom} 58%, ${activeScene.palette.ground} 58%, ${activeScene.palette.ground} 100%)`,
              minHeight: 720,
            }}
          >
            <div className="absolute inset-0">
              <div className="absolute left-[10%] top-[10%] h-20 w-20 rounded-full bg-white/55 blur-sm" />
              <div className="absolute left-[12%] top-[12%] h-24 w-24 rounded-full bg-[#fff4b0]/85" />
              <div className="absolute left-[65%] top-[13%] h-10 w-28 rounded-full bg-white/65 animate-[float_8s_ease-in-out_infinite]" />
              <div className="absolute left-[72%] top-[18%] h-10 w-24 rounded-full bg-white/50 animate-[float_6.5s_ease-in-out_infinite]" />
              <div className="absolute bottom-[12%] left-0 h-40 w-full bg-[radial-gradient(circle_at_bottom,#ffffff12_0%,transparent_65%)]" />
            </div>

            <House mode={activeScene.mode} />

            <Character name="Anna" color="#f47c7c" x="18%" y={activeScene.mode === "school" ? "14%" : "12%"} active={activeScene.id === "anna"} bounce />
            <Character name="Ben" color="#59a5d8" x="42%" y={activeScene.mode === "school" ? "16%" : "11%"} active={activeScene.id === "ben"} bounce />
            <Character name="Caleb" color="#7bc96f" x="66%" y={activeScene.mode === "dinner" ? "16%" : "12%"} active={activeScene.id === "caleb"} bounce />

            {activeScene.mode === "chaos" ? (
              <>
                <div className="absolute left-[14%] top-[26%] rounded-full bg-white/92 px-4 py-2 text-lg font-black text-alert shadow-lg animate-[float_1.7s_ease-in-out_infinite]">
                  CRASH!
                </div>
                <div className="absolute right-[12%] top-[22%] rounded-full bg-white/92 px-4 py-2 text-lg font-black text-alert shadow-lg animate-[float_2s_ease-in-out_infinite]">
                  BANG!
                </div>
                <div className="absolute left-[28%] top-[18%] h-8 w-20 rotate-[18deg] rounded-full bg-stone shadow-lg animate-[spinSpoon_1.2s_linear_infinite]" />
                <div className="absolute right-[26%] top-[46%] h-14 w-14 rounded-2xl bg-clay shadow-lg animate-[boxTumble_1.3s_ease-in-out_infinite]" />
              </>
            ) : null}

            {activeScene.mode === "lesson" ? (
              <div className="absolute left-1/2 top-[18%] flex -translate-x-1/2 gap-4 rounded-[2rem] bg-white/86 px-6 py-4 shadow-xl">
                <div className="h-24 w-3 rounded-full bg-bark" />
                <div className="h-24 w-3 rounded-full bg-bark" />
                <div className="h-24 w-3 rounded-full bg-bark" />
                <div className="absolute inset-x-4 top-1/2 h-1 -translate-y-1/2 bg-alert/80" />
              </div>
            ) : null}

            {activeScene.id === "anna" ? (
              <div className="absolute left-1/2 top-[17%] grid -translate-x-1/2 grid-cols-4 gap-1 rounded-[1.5rem] bg-white/20 p-4">
                {Array.from({ length: 16 }).map((_, index) => (
                  <div
                    key={`block-${index}`}
                    className={`h-8 w-8 rounded-lg border border-white/70 ${beatIndex >= 2 && index > 6 ? "animate-[blockDrop_0.9s_ease-in-out_infinite]" : ""}`}
                    style={{ backgroundColor: ["#f47c7c", "#59a5d8", "#f6bd60", "#7bc96f"][index % 4] }}
                  />
                ))}
              </div>
            ) : null}

            {activeScene.mode === "school" ? (
              <div className="absolute left-[12%] top-[16%] right-[12%] rounded-[2rem] border border-white/50 bg-white/34 p-5 shadow-lg">
                <div className="mb-3 h-4 w-32 rounded-full bg-bark/15" />
                <div className="grid grid-cols-6 gap-3">
                  {Array.from({ length: 12 }).map((_, index) => (
                    <div
                      key={`paper-${index}`}
                      className={`h-9 rounded-lg ${beatIndex >= 3 ? "animate-[paperLift_2.2s_ease-in-out_infinite]" : "rotate-[8deg]"}`}
                      style={{ backgroundColor: index % 2 === 0 ? "#ffffffd8" : "#f6bd60d4" }}
                    />
                  ))}
                </div>
              </div>
            ) : null}

            {activeScene.mode === "dinner" ? (
              <>
                <div className="absolute left-1/2 top-[46%] h-12 w-[70%] -translate-x-1/2 rounded-full bg-bark shadow-xl" />
                <div className="absolute left-[28%] top-[38%] h-16 w-16 rounded-full border-4 border-white/70 bg-[#4f8edc] shadow-lg animate-[cupBob_1.6s_ease-in-out_infinite]" />
              </>
            ) : null}

            {activeScene.mode === "montage" || activeScene.mode === "finale" ? (
              <>
                <div className="absolute left-[8%] top-[16%] rounded-full bg-white/88 px-4 py-2 text-sm font-black text-moss shadow-lg">
                  Share
                </div>
                <div className="absolute right-[9%] top-[19%] rounded-full bg-white/88 px-4 py-2 text-sm font-black text-moss shadow-lg">
                  Help
                </div>
                <div className="absolute left-[18%] bottom-[28%] rounded-full bg-white/88 px-4 py-2 text-sm font-black text-moss shadow-lg">
                  Speak kindly
                </div>
                <div className="absolute right-[15%] bottom-[24%] rounded-full bg-white/88 px-4 py-2 text-sm font-black text-moss shadow-lg">
                  Together
                </div>
              </>
            ) : null}

            {activeScene.mode === "finale" ? (
              <>
                {Array.from({ length: 10 }).map((_, index) => (
                  <div
                    key={`spark-${index}`}
                    className="absolute h-4 w-4 rounded-full bg-white/80 animate-[sparkle_2.4s_ease-in-out_infinite]"
                    style={{
                      left: `${10 + index * 8}%`,
                      top: `${10 + (index % 4) * 12}%`,
                      animationDelay: `${index * 0.18}s`,
                    }}
                  />
                ))}
              </>
            ) : null}

            <div className="absolute inset-x-5 bottom-5 rounded-[1.7rem] border border-white/15 px-5 py-5 text-white shadow-2xl backdrop-blur-md" style={{ backgroundColor: activeScene.palette.card }}>
              <p className="mb-2 text-xs font-semibold uppercase tracking-[0.22em] text-white/70">
                Scene {timeline.findIndex((scene) => scene.id === activeScene.id) + 1} of {timeline.length}
              </p>
              <h2 className="mb-3 text-3xl font-black leading-tight md:text-4xl">{activeScene.beats[beatIndex]}</h2>
              <p className="max-w-3xl text-sm leading-7 text-white/90 md:text-base">{activeScene.narration}</p>
            </div>
          </div>

          <div className="space-y-6">
            <section className="rounded-[2rem] border border-bark/10 bg-white/80 p-6 shadow-[0_18px_45px_rgba(107,76,53,0.1)]">
              <p className="mb-3 text-xs font-semibold uppercase tracking-[0.22em] text-clay">Story Message</p>
              <ul className="space-y-3 text-lg font-semibold text-bark">
                <li>Love one another</li>
                <li>Help each other</li>
                <li>Speak kindly</li>
                <li>Work together</li>
              </ul>
            </section>

            <section className="rounded-[2rem] border border-bark/10 bg-white/80 p-6 shadow-[0_18px_45px_rgba(107,76,53,0.1)]">
              <p className="mb-4 text-xs font-semibold uppercase tracking-[0.22em] text-clay">Scene Timeline</p>
              <div className="space-y-3">
                {timeline.map((scene, index) => {
                  const isActive = scene.id === activeScene.id;
                  return (
                    <div
                      key={scene.id}
                      className={`rounded-[1.4rem] border px-4 py-3 transition ${
                        isActive
                          ? "border-clay bg-parchment shadow-[0_10px_24px_rgba(193,120,79,0.12)]"
                          : "border-bark/10 bg-white"
                      }`}
                    >
                      <div className="flex items-center justify-between gap-4">
                        <div>
                          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-bark/45">Scene {index + 1}</p>
                          <p className="text-sm font-bold text-bark">{scene.title}</p>
                        </div>
                        <div className="text-sm font-semibold text-bark/60">{formatTime(scene.duration)}</div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>
          </div>
        </section>
      </div>

      <style jsx>{`
        @keyframes houseShake {
          0%, 100% { transform: translateX(-50%) rotate(0deg); }
          25% { transform: translateX(calc(-50% - 5px)) rotate(-1.2deg); }
          75% { transform: translateX(calc(-50% + 5px)) rotate(1.2deg); }
        }
        @keyframes houseHum {
          0%, 100% { transform: translateX(-50%) translateY(0); }
          50% { transform: translateX(-50%) translateY(-6px); }
        }
        @keyframes float {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-10px); }
        }
        @keyframes spinSpoon {
          0% { transform: rotate(0deg) translateY(0); }
          50% { transform: rotate(180deg) translateY(-10px); }
          100% { transform: rotate(360deg) translateY(0); }
        }
        @keyframes boxTumble {
          0%, 100% { transform: rotate(0deg); }
          50% { transform: rotate(18deg) translateY(10px); }
        }
        @keyframes blockDrop {
          0%, 100% { transform: translateY(0) rotate(0deg); opacity: 1; }
          50% { transform: translateY(18px) rotate(9deg); opacity: 0.9; }
        }
        @keyframes paperLift {
          0%, 100% { transform: translateY(0) rotate(0deg); }
          50% { transform: translateY(-24px) rotate(8deg); }
        }
        @keyframes cupBob {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-8px); }
        }
        @keyframes sparkle {
          0%, 100% { opacity: 0.2; transform: scale(0.7); }
          50% { opacity: 1; transform: scale(1.25); }
        }
      `}</style>
    </div>
  );
}
