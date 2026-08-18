"use client";

import { Call, Device } from "@twilio/voice-sdk";
import { forwardRef, useCallback, useEffect, useImperativeHandle, useRef, useState } from "react";

type DiallerStage =
  | "idle"
  | "checking"
  | "connecting"
  | "ringing"
  | "connected"
  | "ending"
  | "ended"
  | "failed";

const STAGE_TEXT: Record<DiallerStage, string> = {
  idle: "Idle",
  checking: "Checking permission and connecting…",
  connecting: "Connecting…",
  ringing: "Ringing…",
  connected: "Connected",
  ending: "Ending call…",
  ended: "Call ended — choose the outcome below",
  failed: "Failed",
};

type LogLine = { time: string; text: string };

type TwilioErrorInfo = { message: string; code?: number };

export type CrmDiallerHandle = {
  start: () => Promise<void>;
};

type CrmDiallerProps = {
  contactId: string | null;
  callingEnabled: boolean;
  readinessReady: boolean;
  awaitingDisposition: boolean;
  onCallSession: (sessionId: string) => void;
  onCallEnded: () => void;
  onCallError: (message: string) => void;
  onStartFailure: (message: string) => void;
  onCallReset: () => void;
  onCallPending: (pending: boolean) => void;
};

async function jsonRequest(url: string, init?: RequestInit) {
  const response = await fetch(url, {
    ...init,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(typeof data?.detail === "string" ? data.detail : "The CRM request failed.");
  return data;
}

function formatDuration(totalSeconds: number) {
  const seconds = Math.max(0, Math.floor(totalSeconds));
  const minutes = Math.floor(seconds / 60);
  return `${String(minutes).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}

const CHECKING_TIMEOUT_MS = 20_000;

const CrmDialler = forwardRef<CrmDiallerHandle, CrmDiallerProps>(function CrmDialler(
  {
    contactId,
    callingEnabled,
    readinessReady,
    awaitingDisposition,
    onCallSession,
    onCallEnded,
    onCallError,
    onStartFailure,
    onCallReset,
    onCallPending,
  },
  ref,
) {
  const [stage, setStage] = useState<DiallerStage>("idle");
  const [stageText, setStageText] = useState(STAGE_TEXT.idle);
  const [stageSince, setStageSince] = useState(0);
  const [now, setNow] = useState(() => Date.now());
  const [connectedSince, setConnectedSince] = useState(0);
  const [logLines, setLogLines] = useState<LogLine[]>([]);
  const [checkingTimedOut, setCheckingTimedOut] = useState(false);
  const [muted, setMuted] = useState(false);
  const [twilioError, setTwilioError] = useState<TwilioErrorInfo | null>(null);
  const [copied, setCopied] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  const deviceRef = useRef<Device | null>(null);
  const activeCallRef = useRef<Call | null>(null);
  const startingRef = useRef(false);
  const cancelledRef = useRef(false);

  const addLog = useCallback((text: string) => {
    setLogLines((lines) => [
      ...lines.slice(-49),
      { time: new Date().toLocaleTimeString("en-GB", { hour12: false }), text },
    ]);
  }, []);

  const transition = useCallback(
    (next: DiallerStage, text?: string) => {
      setStage(next);
      setStageText(text ?? STAGE_TEXT[next]);
      setStageSince(Date.now());
      setNow(Date.now());
      addLog(text ?? STAGE_TEXT[next]);
    },
    [addLog],
  );

  const resetToIdle = useCallback(() => {
    setStage("idle");
    setStageText(STAGE_TEXT.idle);
    setStageSince(0);
    setConnectedSince(0);
    setMuted(false);
    setTwilioError(null);
    setCheckingTimedOut(false);
    setCopied(false);
    setLogLines([]);
  }, []);

  const handleDeviceError = useCallback(
    (twilioError: { message: string; code?: number }) => {
      setTwilioError({ message: twilioError.message, code: twilioError.code });
      transition("failed");
      onCallError(`Calling error: ${twilioError.message}`);
    },
    [onCallError, transition],
  );

  const wireCallEvents = useCallback(
    (call: Call) => {
      call.on("accept", () => {
        setConnectedSince(Date.now());
        setMuted(false);
        transition("connected");
      });
      call.on("ringing", () => transition("ringing"));
      call.on("disconnect", () => {
        activeCallRef.current = null;
        setMuted(false);
        transition("ended");
        onCallEnded();
      });
      call.on("cancel", () => {
        activeCallRef.current = null;
        setMuted(false);
        transition("ended", "Call cancelled — choose the outcome below");
        onCallEnded();
      });
      call.on("error", (twilioError: { message: string; code?: number }) => {
        activeCallRef.current = null;
        setMuted(false);
        setTwilioError({ message: twilioError.message, code: twilioError.code });
        transition("failed");
        onCallError(`Call failed: ${twilioError.message}`);
        onCallEnded();
      });
    },
    [onCallEnded, onCallError, transition],
  );

  const start = useCallback(async () => {
    if (!contactId || !callingEnabled || !readinessReady || startingRef.current) return;
    startingRef.current = true;
    cancelledRef.current = false;
    setDismissed(false);
    setCopied(false);
    setTwilioError(null);
    setCheckingTimedOut(false);
    setMuted(false);
    setConnectedSince(0);
    onCallPending(true);
    deviceRef.current?.destroy();
    deviceRef.current = null;
    activeCallRef.current = null;
    transition("checking");
    try {
      const tokenData = await jsonRequest("/api/v1/crm/twilio/token");
      if (cancelledRef.current) return;
      const authorization = await jsonRequest(
        `/api/v1/crm/contacts/${contactId}/calls/authorize`,
        { method: "POST" },
      );
      if (cancelledRef.current) return;
      const device = new Device(tokenData.token, {
        edge: tokenData.edge,
        logLevel: "warn",
        closeProtection: true,
      });
      device.on("error", handleDeviceError);
      deviceRef.current = device;
      onCallSession(authorization.id);
      transition("connecting");
      const call = await device.connect({ params: { authorization: authorization.authorization } });
      if (cancelledRef.current) return;
      activeCallRef.current = call;
      wireCallEvents(call);
    } catch (caught) {
      if (cancelledRef.current) return;
      const message = caught instanceof Error ? caught.message : "Could not start the call.";
      setTwilioError({ message });
      transition("failed");
      onStartFailure(message);
    } finally {
      startingRef.current = false;
      onCallPending(false);
    }
  }, [
    contactId,
    callingEnabled,
    readinessReady,
    handleDeviceError,
    onCallPending,
    onCallSession,
    onStartFailure,
    transition,
    wireCallEvents,
  ]);

  useImperativeHandle(ref, () => ({ start }), [start]);

  const endCall = useCallback(() => {
    if (!activeCallRef.current || stage === "ending") return;
    transition("ending");
    activeCallRef.current.disconnect();
  }, [stage, transition]);

  const toggleMute = useCallback(() => {
    const call = activeCallRef.current;
    if (!call) return;
    setMuted((current) => {
      const next = !current;
      call.mute(next);
      addLog(next ? "Microphone muted" : "Microphone unmuted");
      return next;
    });
  }, [addLog]);

  const cancelChecking = useCallback(() => {
    cancelledRef.current = true;
    deviceRef.current?.destroy();
    deviceRef.current = null;
    addLog("Cancelled while connecting");
    onCallReset();
    onCallPending(false);
    resetToIdle();
  }, [addLog, onCallPending, onCallReset, resetToIdle]);

  // Destroy the single Twilio Device on unmount (page-level cleanup moved here).
  useEffect(() => {
    return () => {
      activeCallRef.current?.disconnect();
      activeCallRef.current = null;
      deviceRef.current?.destroy();
      deviceRef.current = null;
    };
  }, []);

  // Ticking clock while a stage has visible elapsed time.
  useEffect(() => {
    if (stage !== "checking" && stage !== "connecting" && stage !== "ringing" && stage !== "connected") return;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [stage]);

  // Hint + Cancel once "Checking permission and connecting…" (or the connect
  // phase, which can stall on the browser microphone prompt) exceeds 20s.
  useEffect(() => {
    if (stage !== "checking" && stage !== "connecting") return;
    setCheckingTimedOut(false);
    const id = setTimeout(() => setCheckingTimedOut(true), CHECKING_TIMEOUT_MS);
    return () => clearTimeout(id);
  }, [stage]);

  // Once the page resolves the pending disposition, return the dialler to Idle.
  const prevAwaiting = useRef(awaitingDisposition);
  useEffect(() => {
    if (prevAwaiting.current && !awaitingDisposition && (stage === "ended" || stage === "failed")) {
      resetToIdle();
    }
    prevAwaiting.current = awaitingDisposition;
  }, [awaitingDisposition, resetToIdle, stage]);

  // Escape dismisses the open panel.
  useEffect(() => {
    if (dismissed || (stage === "idle" && !awaitingDisposition)) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setDismissed(true);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [dismissed, stage, awaitingDisposition]);

  // Keep the log scrolled to the newest line.
  const logRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    const element = logRef.current;
    if (element) element.scrollTop = element.scrollHeight;
  }, [logLines]);

  const copyError = async () => {
    if (!twilioError) return;
    const text = twilioError.code != null ? `${twilioError.message} (code ${twilioError.code})` : twilioError.message;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  };

  const visible = stage !== "idle" || awaitingDisposition;
  if (!visible) return null;

  const dotClass =
    stage === "connected"
      ? "bg-moss"
      : stage === "ended" || stage === "failed"
        ? "bg-alert"
        : stage === "idle"
          ? "bg-stone"
          : "bg-amber animate-pulse";

  const elapsedSeconds = stageSince ? Math.max(0, Math.floor((now - stageSince) / 1000)) : 0;
  const connectedDuration = connectedSince ? formatDuration((now - connectedSince) / 1000) : "00:00";

  const pillLabel = (() => {
    if (stage === "connected") return `Connected · ${connectedDuration}`;
    if (stage === "ringing") return `Ringing · ${elapsedSeconds}s`;
    if (stage === "checking") return "Checking permission…";
    if (stage === "connecting") return "Connecting…";
    if (stage === "ending") return "Ending call…";
    if (stage === "ended") return "Call ended — outcome needed";
    if (stage === "failed") return "Call failed";
    return "Previous call ended — outcome needed";
  })();

  if (dismissed) {
    return (
      <button
        type="button"
        onClick={() => setDismissed(false)}
        aria-label={`Reopen call panel — ${pillLabel}`}
        className="fixed right-4 top-4 z-[100] flex items-center gap-2 rounded-full border border-stone bg-charcoal px-4 py-2 text-sm font-semibold text-cream shadow-xl hover:bg-black/80"
      >
        <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${dotClass}`} />
        <span>{pillLabel}</span>
      </button>
    );
  }

  return (
    <aside
      role="region"
      aria-label="Call dialler"
      className="fixed right-4 top-4 z-[100] w-80 max-w-[calc(100vw-2rem)] rounded-2xl border border-stone bg-charcoal p-4 text-cream shadow-2xl"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-2">
          <span className={`mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full ${dotClass}`} />
          <div className="min-w-0">
            <div aria-live="polite" className="text-sm font-bold leading-snug">
              {stage === "idle" && awaitingDisposition
                ? "Previous call ended — choose the outcome below"
                : stageText}
            </div>
            <div className="mt-0.5 text-[11px] text-cream/50">
              {stageSince ? new Date(stageSince).toLocaleTimeString("en-GB", { hour12: false }) : "—"}
              {stage === "checking" || stage === "connecting" || stage === "ringing"
                ? ` · ${elapsedSeconds}s`
                : stage === "connected"
                  ? ` · ${connectedDuration}`
                  : ""}
            </div>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setDismissed(true)}
          aria-label="Dismiss call panel"
          className="-mr-1 -mt-1 rounded-lg px-2 py-1 text-cream/60 hover:bg-white/10 hover:text-cream"
        >
          ✕
        </button>
      </div>

      <div className="mt-3">
        {stage === "checking" && (
          <div className="flex items-center gap-2 text-sm text-cream/80">
            <span aria-hidden="true" className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-cream/30 border-t-cream" />
            <span className="min-w-0">{checkingTimedOut ? "Still waiting — see the hint below" : "Checking permission and connecting…"}</span>
          </div>
        )}
        {stage === "connecting" && (
          <div className="flex items-center gap-2 text-sm text-cream/80">
            <span aria-hidden="true" className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-cream/30 border-t-cream" />
            <span>Connecting…</span>
          </div>
        )}
        {stage === "ringing" && (
          <div className="text-2xl font-bold tabular-nums text-amber">Ringing · {elapsedSeconds}s</div>
        )}
        {stage === "connected" && (
          <div className="text-3xl font-bold tabular-nums" aria-live="polite">
            {connectedDuration}
          </div>
        )}
        {stage === "ending" && <div className="text-sm text-cream/70">Ending call…</div>}
        {stage === "ended" && (
          <p className="rounded-xl bg-black/20 p-3 text-sm leading-snug text-cream/80">
            Choose the outcome in the Call queue panel — this window won&apos;t block it.
          </p>
        )}
        {stage === "idle" && awaitingDisposition && (
          <p className="rounded-xl bg-black/20 p-3 text-sm leading-snug text-cream/80">
            A previous call is waiting for an outcome in the Call queue panel.
          </p>
        )}
      </div>

      {(stage === "ringing" || stage === "connected" || stage === "ending") && (
        <div className="mt-3 flex gap-2">
          {stage === "connected" && (
            <button
              type="button"
              onClick={toggleMute}
              aria-pressed={muted}
              className="flex-1 rounded-xl border border-cream/30 px-4 py-2 text-sm font-bold hover:bg-white/10"
            >
              {muted ? "Unmute" : "Mute"}
            </button>
          )}
          <button
            type="button"
            onClick={endCall}
            disabled={stage === "ending"}
            className={`flex-1 rounded-xl px-4 py-2 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-50 ${stage === "ending" ? "bg-alert/60" : "bg-alert hover:bg-alert/90"}`}
          >
            End call
          </button>
        </div>
      )}

      {(stage === "checking" || stage === "connecting") && checkingTimedOut && (
        <div className="mt-3 rounded-xl border border-amber/40 bg-amber/10 p-3 text-sm">
          <p className="font-semibold text-amber">
            Taking too long? Check the microphone prompt near the address bar and allow it
          </p>
          <button
            type="button"
            onClick={cancelChecking}
            className="mt-2 rounded-lg bg-alert px-4 py-2 text-sm font-bold text-white hover:bg-alert/90"
          >
            Cancel
          </button>
        </div>
      )}

      {stage === "failed" && twilioError && (
        <div className="mt-3 rounded-xl border border-alert/40 bg-alert/10 p-3">
          <p className="text-sm font-bold text-alert">Call failed</p>
          <p className="mt-1 break-words text-xs leading-relaxed text-cream/80">
            {twilioError.message}
            {twilioError.code != null ? ` (code ${twilioError.code})` : ""}
          </p>
          <button
            type="button"
            onClick={() => void copyError()}
            className="mt-2 rounded-lg border border-cream/30 px-3 py-1.5 text-xs font-semibold hover:bg-white/10"
          >
            {copied ? "Copied" : "Copy error"}
          </button>
        </div>
      )}

      <div className="mt-3">
        <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-cream/40">Call log</div>
        <div
          ref={logRef}
          className="mt-1 max-h-32 space-y-0.5 overflow-y-auto rounded-xl bg-black/20 p-2 text-xs text-cream/70"
        >
          {logLines.map((line, index) => (
            <div key={`${line.time}-${index}`} className="flex gap-2 leading-snug">
              <span className="shrink-0 font-mono text-cream/40">{line.time}</span>
              <span className="min-w-0">{line.text}</span>
            </div>
          ))}
          {!logLines.length && <p className="py-1 text-cream/40">No events yet.</p>}
        </div>
      </div>
    </aside>
  );
});

export default CrmDialler;
