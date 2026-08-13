"use client";

import { Call, Device } from "@twilio/voice-sdk";
import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";


type CrmContact = {
  id: string;
  provider_id: string | null;
  first_name: string;
  last_name: string;
  job_title: string | null;
  company_name: string | null;
  email: string | null;
  phone_e164: string | null;
  lifecycle_stage: string;
  provider_name: string | null;
  provider_slug: string | null;
  region: string | null;
  local_authority: string | null;
  overall_rating: string | null;
  subscriber_type: string;
  email_marketing_basis: string;
  phone_screening_status: string;
  phone_screened_at: string | null;
  call_suppressed: boolean;
  email_suppressed: boolean;
};

type CrmCompany = {
  id: string;
  name: string;
  website: string | null;
  phone_e164: string | null;
  address: string | null;
  notes: string | null;
  updated_at: string;
};

type CrmTask = {
  id: string;
  contact_id: string;
  task_type: string;
  title: string;
  due_at: string;
  priority: string;
  provider_name: string | null;
  first_name: string;
  last_name: string;
};

type CrmDeal = {
  id: string;
  contact_id: string;
  title: string;
  stage: string;
  value_pence: number;
  loss_reason: string | null;
  company_name: string | null;
  provider_name: string | null;
  first_name: string;
  last_name: string;
  updated_at: string;
};

type RecentCall = {
  id: string;
  contact_id: string;
  agent_user_id: number;
  status: string;
  duration_seconds: number | null;
  disposition: string | null;
  started_at: string | null;
  provider_name: string | null;
  company_name: string | null;
  first_name: string;
  last_name: string;
  agent: string;
  recording_id: string | null;
  recording_status: string | null;
  intelligence_status: string | null;
};

type Summary = {
  role: string;
  counts: {
    contacts?: number;
    companies?: number;
    open_tasks?: number;
    won_deals?: number;
    calls?: number;
    campaigns?: number;
  };
  contacts: CrmContact[];
  companies: CrmCompany[];
  tasks: CrmTask[];
  deals: CrmDeal[];
  recent_calls: RecentCall[];
  pending_disposition_call: { id: string; contact_id: string; status: string } | null;
  calling: {
    enabled: boolean;
    recording_enabled: boolean;
    recording_retention_days: number;
    test_numbers_only: boolean;
  };
  features: {
    email_campaigns_enabled: boolean;
    uk_sms_enabled: boolean;
    ai_enabled: boolean;
  };
};

type Activity = {
  id: string;
  activity_type: string;
  body: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
};

type Campaign = {
  id: string;
  name: string;
  subject: string;
  status: string;
  recipient_count: number;
  sent_count: number;
  failed_count: number;
  delivered_count: number;
  bounced_count: number;
  complained_count: number;
  unsubscribed_count: number;
  created_at: string;
};

type PerformanceReport = {
  start: string;
  end: string;
  agents: Array<{
    agent_user_id: number;
    agent: string;
    calls: number;
    connected_calls: number;
    talk_seconds: number;
    dispositioned_calls: number;
    positive_outcomes: number;
    average_qa_score: number | null;
  }>;
  dispositions: Array<{ outcome: string; count: number }>;
  campaigns: Record<string, number>;
  ai_advisory_only: boolean;
};

type CallDetail = {
  id: string;
  status: string;
  disposition: string | null;
  duration_seconds: number | null;
  recording_id: string | null;
  recording_status: string | null;
  recording_expires_at: string | null;
  intelligence_status: string | null;
  transcript: string | null;
  summary: string | null;
  evaluation: {
    overall_qa_score?: number;
    overall_score?: number;
    suggested_disposition?: string;
    customer_sentiment?: string;
    outcome?: string;
    strengths?: string[];
    coaching_actions?: string[];
    compliance_flags?: string[];
  } | null;
};

type Tab = "workspace" | "pipeline" | "campaigns" | "reports" | "compliance";

const STAGES = [
  "new", "assigned", "attempting_contact", "connected", "qualified",
  "demo_booked", "proposal_sent", "negotiation", "won", "lost", "suppressed",
];

const PRIMARY_DISPOSITIONS = [
  ["no_contact", "No contact"],
  ["connected", "Connected"],
  ["callback", "Callback"],
  ["do_not_call", "Do not call"],
] as const;

const SECONDARY_DISPOSITIONS: Record<string, Array<[string, string]>> = {
  no_contact: [["no_answer", "No answer"], ["busy", "Busy"], ["voicemail", "Voicemail"], ["gatekeeper", "Gatekeeper"]],
  connected: [["connected", "Conversation completed"], ["qualified", "Qualified"], ["meeting_booked", "Meeting booked"], ["sale_completed", "Sale"], ["not_interested", "Not interested"]],
  do_not_call: [["do_not_call", "Contact said do not call"], ["wrong_number", "Wrong number"]],
};

const TERMINAL_CALL_STATUSES = new Set(["completed", "busy", "no_answer", "failed", "canceled"]);

function label(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

function contactName(contact: Pick<CrmContact, "provider_name" | "company_name" | "first_name" | "last_name">) {
  return contact.provider_name || contact.company_name || `${contact.first_name} ${contact.last_name}`.trim() || "Unnamed contact";
}

function pounds(pence: number) {
  return new Intl.NumberFormat("en-GB", { style: "currency", currency: "GBP" }).format(pence / 100);
}

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

async function formRequest(url: string, body: FormData) {
  const response = await fetch(url, { method: "POST", credentials: "include", body });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(typeof data?.detail === "string" ? data.detail : "The import failed.");
  return data;
}

function screeningState(contact: CrmContact | null, summary: Summary | null) {
  if (!contact?.phone_e164) return { ready: false, tone: "bg-dusk", title: "No phone number", detail: "Add a UK number first." };
  if (contact.call_suppressed || ["tps", "ctps"].includes(contact.phone_screening_status)) {
    return { ready: false, tone: "bg-alert", title: "Do not call", detail: "TPS/CTPS or a CareGist objection blocks this number." };
  }
  if (summary?.calling.test_numbers_only) {
    return { ready: true, tone: "bg-amber", title: "Pilot test number", detail: "Only the approved Twilio test list can be called." };
  }
  const checked = contact.phone_screened_at ? new Date(contact.phone_screened_at).getTime() : 0;
  const fresh = checked > Date.now() - 28 * 24 * 60 * 60 * 1000;
  if (["clear", "consent_override"].includes(contact.phone_screening_status) && fresh) {
    return { ready: true, tone: "bg-moss", title: "Ready to call", detail: `Screened ${new Date(checked).toLocaleDateString("en-GB")}.` };
  }
  return { ready: false, tone: "bg-amber", title: "Needs screening", detail: "A manager must import or record fresh TPS/CTPS evidence." };
}

export default function CrmPage() {
  const [tab, setTab] = useState<Tab>("workspace");
  const [summary, setSummary] = useState<Summary | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [timeline, setTimeline] = useState<Activity[]>([]);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [report, setReport] = useState<PerformanceReport | null>(null);
  const [callDetail, setCallDetail] = useState<CallDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [note, setNote] = useState("");
  const [callStatus, setCallStatus] = useState("Idle");
  const [callSessionId, setCallSessionId] = useState<string | null>(null);
  const [awaitingDisposition, setAwaitingDisposition] = useState(false);
  const [dispositionGroup, setDispositionGroup] = useState<string | null>(null);
  const [callbackAt, setCallbackAt] = useState("");
  const [standaloneCallbackAt, setStandaloneCallbackAt] = useState("");
  const [standaloneTaskType, setStandaloneTaskType] = useState("call");
  const [standaloneTaskTitle, setStandaloneTaskTitle] = useState("");
  const [standaloneTaskPriority, setStandaloneTaskPriority] = useState("normal");
  const [activeCall, setActiveCall] = useState<Call | null>(null);
  const [callActionPending, setCallActionPending] = useState(false);
  const [campaignDraftId, setCampaignDraftId] = useState<string | null>(null);
  const [recipientIds, setRecipientIds] = useState<string[]>([]);
  const [confirmCampaign, setConfirmCampaign] = useState(false);
  const [pendingLostDeal, setPendingLostDeal] = useState<CrmDeal | null>(null);
  const [lossReason, setLossReason] = useState("");
  const deviceRef = useRef<Device | null>(null);
  const callActionRef = useRef(false);

  const selected = summary?.contacts.find((contact) => contact.id === selectedId) || null;
  const manager = summary?.role === "owner" || summary?.role === "admin";
  const readiness = screeningState(selected, summary);
  const eligibleEmailContacts = useMemo(
    () => (summary?.contacts || []).filter((contact) => (
      Boolean(contact.email)
      && !contact.email_suppressed
      && contact.email_marketing_basis !== "none"
      && (
        contact.email_marketing_basis !== "corporate_subscriber"
        || contact.subscriber_type === "corporate"
      )
    )),
    [summary],
  );

  const showError = (caught: unknown, fallback: string) => {
    setError(caught instanceof Error ? caught.message : fallback);
    setNotice("");
  };

  const showNotice = (message: string) => {
    setNotice(message);
    setError("");
  };

  const loadSummary = useCallback(async () => {
    try {
      const data = await jsonRequest("/api/v1/crm/summary");
      setSummary(data);
      setSelectedId((current) => data.pending_disposition_call?.contact_id || current || data.contacts?.[0]?.id || null);
      if (data.pending_disposition_call) {
        setCallSessionId(data.pending_disposition_call.id);
        setAwaitingDisposition(true);
        setCallStatus("Previous call ended — choose the outcome below");
      }
      setError("");
    } catch (caught) {
      showError(caught, "Could not load the CRM.");
    } finally {
      setLoading(false);
    }
  }, []);

  const loadCampaigns = useCallback(async () => {
    try {
      const data = await jsonRequest("/api/v1/crm/campaigns");
      setCampaigns(Array.isArray(data.data) ? data.data : []);
    } catch (caught) {
      showError(caught, "Could not load email campaigns.");
    }
  }, []);

  const loadReport = useCallback(async () => {
    try {
      setReport(await jsonRequest("/api/v1/crm/reports/performance"));
    } catch (caught) {
      showError(caught, "Could not load performance reporting.");
    }
  }, []);

  const loadCallDetail = useCallback(async (callId: string) => {
    try {
      setCallDetail(await jsonRequest(`/api/v1/crm/calls/${callId}`));
      setTab("reports");
    } catch (caught) {
      showError(caught, "Could not load the call record.");
    }
  }, []);

  useEffect(() => {
    void loadSummary();
    return () => deviceRef.current?.destroy();
  }, [loadSummary]);

  useEffect(() => {
    if (!selectedId) {
      setTimeline([]);
      return;
    }
    jsonRequest(`/api/v1/crm/contacts/${selectedId}/timeline`)
      .then((data) => setTimeline(Array.isArray(data.data) ? data.data : []))
      .catch((caught) => showError(caught, "Could not load activity."));
  }, [selectedId]);

  useEffect(() => {
    if (tab === "campaigns" && summary?.features.email_campaigns_enabled) void loadCampaigns();
    if (tab === "reports" && manager) void loadReport();
  }, [tab, manager, loadCampaigns, loadReport, summary?.features.email_campaigns_enabled]);

  useEffect(() => {
    if (!summary || manager || callSessionId || activeCall) return;
    const unresolved = summary.recent_calls.find(
      (call) => TERMINAL_CALL_STATUSES.has(call.status) && call.disposition === null,
    );
    if (!unresolved) return;
    setCallSessionId(unresolved.id);
    setSelectedId(unresolved.contact_id);
    setAwaitingDisposition(true);
    setCallStatus("Call ended — choose the outcome below");
  }, [activeCall, callSessionId, manager, summary]);

  async function createContact(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    setBusy(true);
    try {
      const contact = await jsonRequest("/api/v1/crm/contacts", {
        method: "POST",
        body: JSON.stringify({
          provider_id: form.get("provider_id") || null,
          company_id: form.get("company_id") || null,
          first_name: form.get("first_name") || "",
          last_name: form.get("last_name") || "",
          company_name: form.get("company_name") || null,
          email: form.get("email") || null,
          phone_e164: form.get("phone_e164") || null,
        }),
      });
      formElement.reset();
      setSelectedId(contact.id);
      showNotice("Contact added. CareGist checked the local screening cache automatically.");
      await loadSummary();
    } catch (caught) {
      showError(caught, "Could not add the contact.");
    } finally {
      setBusy(false);
    }
  }

  async function createCompany(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    try {
      await jsonRequest("/api/v1/crm/companies", {
        method: "POST",
        body: JSON.stringify({
          name: form.get("name"),
          website: form.get("website") || null,
          phone_e164: form.get("phone_e164") || null,
          address: form.get("address") || null,
          notes: null,
        }),
      });
      formElement.reset();
      showNotice("Company added.");
      await loadSummary();
    } catch (caught) {
      showError(caught, "Could not add the company.");
    }
  }

  async function addNote(event: FormEvent) {
    event.preventDefault();
    if (!selected || !note.trim()) return;
    try {
      await jsonRequest(`/api/v1/crm/contacts/${selected.id}/notes`, {
        method: "POST",
        body: JSON.stringify({ body: note }),
      });
      setNote("");
      const data = await jsonRequest(`/api/v1/crm/contacts/${selected.id}/timeline`);
      setTimeline(data.data || []);
    } catch (caught) {
      showError(caught, "Could not save the note.");
    }
  }

  async function changeStage(stage: string) {
    if (!selected) return;
    try {
      await jsonRequest(`/api/v1/crm/contacts/${selected.id}/stage`, {
        method: "PATCH",
        body: JSON.stringify({ stage }),
      });
      await loadSummary();
    } catch (caught) {
      showError(caught, "Could not update the stage.");
    }
  }

  async function completeTask(taskId: string) {
    try {
      await jsonRequest(`/api/v1/crm/tasks/${taskId}/complete`, { method: "POST" });
      showNotice("Task completed.");
      await loadSummary();
    } catch (caught) {
      showError(caught, "Could not complete the task.");
    }
  }

  async function createTask() {
    if (!selected || !standaloneCallbackAt) return;
    const dueAt = new Date(standaloneCallbackAt);
    if (Number.isNaN(dueAt.getTime()) || dueAt <= new Date()) {
      setError("Choose a future callback date and time.");
      return;
    }
    try {
      await jsonRequest(`/api/v1/crm/contacts/${selected.id}/tasks`, {
        method: "POST",
        body: JSON.stringify({
          task_type: standaloneTaskType,
          title: standaloneTaskTitle.trim() || `${label(standaloneTaskType)}: ${contactName(selected)}`,
          due_at: dueAt.toISOString(),
          priority: standaloneTaskPriority,
        }),
      });
      setStandaloneCallbackAt("");
      setStandaloneTaskTitle("");
      showNotice(`${label(standaloneTaskType)} task scheduled for ${dueAt.toLocaleString("en-GB")}.`);
      await loadSummary();
    } catch (caught) {
      showError(caught, "Could not schedule the callback.");
    }
  }

  async function startCall() {
    if (!selected || !summary?.calling.enabled || !readiness.ready || callActionRef.current) return;
    callActionRef.current = true;
    setCallActionPending(true);
    setError("");
    setNotice("");
    setCallStatus("Checking permission and connecting…");
    try {
      const tokenData = await jsonRequest("/api/v1/crm/twilio/token");
      const authorization = await jsonRequest(
        `/api/v1/crm/contacts/${selected.id}/calls/authorize`,
        { method: "POST" },
      );
      deviceRef.current?.destroy();
      const device = new Device(tokenData.token, {
        edge: tokenData.edge,
        logLevel: "warn",
        closeProtection: true,
      });
      device.on("error", (twilioError) => {
        setError(`Calling error: ${twilioError.message}`);
        setCallStatus("Failed");
      });
      deviceRef.current = device;
      setCallSessionId(authorization.id);
      setAwaitingDisposition(false);
      setDispositionGroup(null);
      setCallbackAt("");
      const call = await device.connect({ params: { authorization: authorization.authorization } });
      setActiveCall(call);
      setCallStatus("Connecting…");
      call.on("accept", () => setCallStatus("Connected"));
      call.on("ringing", () => setCallStatus("Ringing…"));
      call.on("disconnect", () => {
        setCallStatus("Call ended — choose the outcome below");
        setActiveCall(null);
        setAwaitingDisposition(true);
      });
      call.on("cancel", () => {
        setCallStatus("Call cancelled — choose the outcome below");
        setActiveCall(null);
        setAwaitingDisposition(true);
      });
      call.on("error", (twilioError) => {
        setError(`Call failed: ${twilioError.message}`);
        setCallStatus("Failed — choose the outcome below");
        setActiveCall(null);
        setAwaitingDisposition(true);
      });
    } catch (caught) {
      setCallStatus("Idle");
      setCallSessionId(null);
      setAwaitingDisposition(false);
      showError(caught, "Could not start the call.");
      await loadSummary();
    } finally {
      callActionRef.current = false;
      setCallActionPending(false);
    }
  }

  async function disposition(value: string, group: string) {
    if (!callSessionId || callActionRef.current) return;
    let callbackIso: string | null = null;
    if (group === "callback") {
      const chosen = new Date(callbackAt);
      if (!callbackAt || Number.isNaN(chosen.getTime()) || chosen <= new Date()) {
        setError("Choose a future callback date and time.");
        return;
      }
      callbackIso = chosen.toISOString();
    }
    const completedCallId = callSessionId;
    callActionRef.current = true;
    setCallActionPending(true);
    try {
      await jsonRequest(`/api/v1/crm/calls/${completedCallId}/disposition`, {
        method: "POST",
        body: JSON.stringify({
          disposition_group: group,
          disposition: value,
          callback_at: callbackIso,
        }),
      });
      setCallSessionId(null);
      setAwaitingDisposition(false);
      setDispositionGroup(null);
      setCallbackAt("");
      setCallStatus("Outcome saved");
      showNotice(`${label(value)} saved. You can start the next call.`);
      await loadSummary();
    } catch (caught) {
      showError(caught, "Could not save the call outcome.");
    } finally {
      callActionRef.current = false;
      setCallActionPending(false);
    }
  }

  async function createDeal(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected) return;
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    try {
      await jsonRequest(`/api/v1/crm/contacts/${selected.id}/deals`, {
        method: "POST",
        body: JSON.stringify({
          title: form.get("title"),
          value_pence: Math.round(Number(form.get("value_gbp") || 0) * 100),
        }),
      });
      formElement.reset();
      showNotice("Deal added to the pipeline.");
      await loadSummary();
    } catch (caught) {
      showError(caught, "Could not create the deal.");
    }
  }

  async function changeDealStage(deal: CrmDeal, stage: string) {
    if (stage === "lost") {
      setPendingLostDeal(deal);
      setLossReason(deal.loss_reason || "");
      return;
    }
    await saveDealStage(deal, stage, null);
  }

  async function saveDealStage(deal: CrmDeal, stage: string, reason: string | null) {
    try {
      await jsonRequest(`/api/v1/crm/deals/${deal.id}/stage`, {
        method: "PATCH",
        body: JSON.stringify({ stage, loss_reason: reason }),
      });
      setPendingLostDeal(null);
      setLossReason("");
      showNotice(`Deal moved to ${label(stage)}.`);
      await loadSummary();
    } catch (caught) {
      showError(caught, "Could not move the deal.");
    }
  }

  async function updateMarketing(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected) return;
    const form = new FormData(event.currentTarget);
    const basis = String(form.get("basis") || "none");
    const reference = String(form.get("reference") || "").trim();
    try {
      await jsonRequest(`/api/v1/crm/contacts/${selected.id}/marketing`, {
        method: "PATCH",
        body: JSON.stringify({
          subscriber_type: form.get("subscriber_type"),
          email_marketing_basis: basis,
          evidence: basis === "none" ? {} : { reference },
        }),
      });
      showNotice("Email permission saved.");
      await loadSummary();
    } catch (caught) {
      showError(caught, "Could not save email permission.");
    }
  }

  async function recordScreening(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected) return;
    const form = new FormData(event.currentTarget);
    try {
      await jsonRequest(`/api/v1/crm/contacts/${selected.id}/phone-screening`, {
        method: "PATCH",
        body: JSON.stringify({
          status: form.get("status"),
          source: form.get("source"),
          source_reference: form.get("reference"),
          screened_at: new Date().toISOString(),
        }),
      });
      showNotice("Phone screening saved. Calling rules updated immediately.");
      await loadSummary();
    } catch (caught) {
      showError(caught, "Could not save phone screening.");
    }
  }

  async function importScreening(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    setBusy(true);
    try {
      const result = await formRequest("/api/v1/crm/phone-screenings/import", form);
      showNotice(`Screening complete: ${result.matched} matched, ${result.suppressed} blocked, ${result.clear} clear.`);
      formElement.reset();
      await loadSummary();
    } catch (caught) {
      showError(caught, "Could not import screening results.");
    } finally {
      setBusy(false);
    }
  }

  async function createCampaign(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    try {
      const campaign = await jsonRequest("/api/v1/crm/campaigns", {
        method: "POST",
        body: JSON.stringify({
          name: form.get("name"),
          subject: form.get("subject"),
          body_text: form.get("body_text"),
        }),
      });
      setCampaignDraftId(campaign.id);
      setRecipientIds([]);
      setConfirmCampaign(false);
      showNotice("Draft created. Choose eligible recipients, confirm, then queue it.");
      await loadCampaigns();
    } catch (caught) {
      showError(caught, "Could not create the campaign.");
    }
  }

  async function launchCampaign() {
    if (!campaignDraftId || !confirmCampaign || recipientIds.length === 0) return;
    setBusy(true);
    try {
      const result = await jsonRequest(`/api/v1/crm/campaigns/${campaignDraftId}/launch`, {
        method: "POST",
        body: JSON.stringify({ contact_ids: recipientIds, confirm_send: true }),
      });
      showNotice(`${result.recipient_count} email${result.recipient_count === 1 ? "" : "s"} queued safely.`);
      setCampaignDraftId(null);
      setRecipientIds([]);
      setConfirmCampaign(false);
      await Promise.all([loadCampaigns(), loadSummary()]);
    } catch (caught) {
      showError(caught, "Could not queue the campaign.");
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <div className="mx-auto max-w-7xl px-6 py-12">Loading CareGist CRM…</div>;

  const navItems: Array<[Tab, string]> = [
    ["workspace", "Call queue"],
    ["pipeline", "Pipeline"],
    ["campaigns", "Email"],
    ["reports", "Reports"],
    ["compliance", "Safety"],
  ];

  return (
    <div className="min-h-screen bg-[#f4f1ea] px-4 py-6 lg:px-8">
      <div className="mx-auto max-w-[1500px]">
        <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="mb-1 text-xs font-semibold uppercase tracking-[0.24em] text-clay">Internal workspace</p>
            <h1 className="text-4xl font-bold text-charcoal">CareGist CRM</h1>
            <p className="mt-2 text-sm text-dusk">Simple outreach, pipeline and quality reporting for the UK team.</p>
          </div>
          <div className="rounded-xl border border-stone bg-cream px-4 py-3 text-sm">
            <div><span className={`mr-2 inline-block h-2.5 w-2.5 rounded-full ${summary?.calling.enabled ? "bg-moss" : "bg-dusk"}`} />Calling {summary?.calling.enabled ? "ready" : "locked until Twilio setup"}</div>
            <div className="mt-1 text-xs text-dusk">
              {summary?.calling.recording_enabled ? `Recording on · automatic ${summary.calling.recording_retention_days}-day deletion` : "Recording off"}
              {" · "}UK SMS disabled
            </div>
          </div>
        </div>

        <div className="mb-5 flex gap-2 overflow-x-auto rounded-2xl border border-stone bg-cream p-2">
          {navItems.map(([value, name]) => (
            <button key={value} aria-current={tab === value ? "page" : undefined} disabled={Boolean(callSessionId) && value !== "workspace"} onClick={() => setTab(value)} className={`whitespace-nowrap rounded-xl px-4 py-2 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-40 ${tab === value ? "bg-charcoal text-white" : "text-dusk hover:bg-parchment"}`}>{name}</button>
          ))}
        </div>

        {error && <div role="alert" aria-live="assertive" className="mb-4 rounded-xl border border-alert bg-white px-4 py-3 text-sm text-alert">{error}</div>}
        {notice && <div role="status" aria-live="polite" className="mb-4 rounded-xl border border-sage bg-white px-4 py-3 text-sm text-moss">{notice}</div>}

        <div className="mb-5 grid grid-cols-2 gap-3 lg:grid-cols-6">
          {[
            ["Contacts", summary?.counts.contacts || 0],
            ["Companies", summary?.counts.companies || 0],
            ["Open tasks", summary?.counts.open_tasks || 0],
            ["Calls", summary?.counts.calls || 0],
            ["Won", summary?.counts.won_deals || 0],
            ["Campaigns", summary?.counts.campaigns || 0],
          ].map(([name, value]) => (
            <div key={name} className="rounded-2xl border border-stone bg-cream p-4">
              <div className="text-xs font-semibold uppercase tracking-wider text-dusk">{name}</div>
              <div className="mt-2 text-3xl font-semibold text-charcoal">{value}</div>
            </div>
          ))}
        </div>

        {tab === "workspace" && (
          <div className="grid gap-4 xl:grid-cols-[310px_minmax(0,1fr)_330px]">
            <aside className="rounded-2xl border border-stone bg-cream p-4">
              <div className="mb-4 flex items-center justify-between"><h2 className="text-xl font-bold">Call queue</h2><span className="rounded-full bg-parchment px-2 py-1 text-xs text-dusk">{summary?.contacts.length || 0}</span></div>
              <div className="max-h-[680px] space-y-2 overflow-y-auto pr-1">
                {summary?.contacts.map((contact) => {
                  const state = screeningState(contact, summary);
                  return (
                    <button key={contact.id} disabled={Boolean(callSessionId) && selectedId !== contact.id} onClick={() => setSelectedId(contact.id)} className={`w-full rounded-xl border p-3 text-left transition disabled:cursor-not-allowed disabled:opacity-40 ${selectedId === contact.id ? "border-clay bg-parchment" : "border-stone bg-white hover:border-dusk"}`}>
                      <div className="flex items-start justify-between gap-2"><div className="font-semibold text-charcoal">{contactName(contact)}</div><span className={`mt-1 h-2.5 w-2.5 shrink-0 rounded-full ${state.tone}`} title={state.title} /></div>
                      <div className="mt-1 text-xs text-dusk">{contact.region || contact.local_authority || contact.phone_e164 || "No territory"}</div>
                      <div className="mt-2 flex items-center justify-between text-[11px] font-semibold uppercase tracking-wider"><span className="text-clay">{label(contact.lifecycle_stage)}</span><span className="text-dusk">{state.title}</span></div>
                    </button>
                  );
                })}
                {!summary?.contacts.length && <p className="py-8 text-center text-sm text-dusk">Add the first contact to begin.</p>}
              </div>
            </aside>

            <section className="rounded-2xl border border-stone bg-cream p-5">
              {!selected ? <div className="flex min-h-[500px] items-center justify-center text-dusk">Select or add a contact.</div> : (
                <>
                  <div className="flex flex-wrap items-start justify-between gap-4 border-b border-stone pb-5">
                    <div><div className="text-xs font-semibold uppercase tracking-[0.2em] text-clay">Current contact</div><h2 className="mt-1 text-3xl font-bold">{contactName(selected)}</h2><p className="mt-2 text-sm text-dusk">{selected.job_title || "Contact"} · {selected.region || "Territory not set"} · {selected.overall_rating || "No published rating"}</p></div>
                    <select aria-label="Lifecycle stage" value={selected.lifecycle_stage} onChange={(event) => void changeStage(event.target.value)} className="rounded-lg border border-stone bg-white px-3 py-2 text-sm">{STAGES.map((stage) => <option key={stage} value={stage}>{label(stage)}</option>)}</select>
                  </div>

                  <div className="my-5 grid gap-3 sm:grid-cols-3">
                    <div className="rounded-xl bg-parchment p-3"><div className="text-xs text-dusk">Phone</div><div className="mt-1 font-medium">{selected.phone_e164 || "Not provided"}</div></div>
                    <div className="rounded-xl bg-parchment p-3"><div className="text-xs text-dusk">Email</div><div className="mt-1 truncate font-medium">{selected.email || "Not provided"}</div></div>
                    <div className="rounded-xl bg-parchment p-3"><div className="text-xs text-dusk">Stage</div><div className="mt-1 font-medium">{label(selected.lifecycle_stage)}</div></div>
                  </div>

                  <div className="rounded-2xl bg-charcoal p-5 text-cream">
                    <div className="flex flex-wrap items-center justify-between gap-4">
                      <div className="flex items-center gap-3"><span className={`h-4 w-4 rounded-full ${readiness.tone}`} /><div><div className="font-bold">{readiness.title}</div><div className="mt-1 text-xs text-stone">{readiness.detail}</div></div></div>
                      {activeCall ? <button onClick={() => activeCall.disconnect()} className="rounded-xl bg-alert px-6 py-3 font-bold text-white">End call</button> : <button onClick={() => void startCall()} disabled={!summary?.calling.enabled || !readiness.ready || Boolean(callSessionId) || callActionPending} className="rounded-xl bg-amber px-6 py-3 font-bold text-charcoal disabled:cursor-not-allowed disabled:opacity-40">{callActionPending ? "Connecting…" : readiness.ready ? "Call contact" : "Calling blocked"}</button>}
                    </div>
                    <div role="status" aria-live="polite" className="mt-4 rounded-lg bg-white/10 px-3 py-2 text-sm">{callStatus}</div>
                    {callSessionId && awaitingDisposition && !activeCall && (
                      <div className="mt-4 border-t border-dusk pt-4">
                        <p className="mb-3 text-sm font-semibold">What happened? Choose one before the next call.</p>
                        <div className="grid gap-2 sm:grid-cols-2">
                          {PRIMARY_DISPOSITIONS.map(([value, name]) => (
                            <button key={value} aria-pressed={dispositionGroup === value} disabled={callActionPending} onClick={() => setDispositionGroup(value)} className={`min-h-16 rounded-xl border px-4 py-3 text-left text-base font-bold disabled:opacity-40 ${dispositionGroup === value ? "border-amber bg-amber text-charcoal" : "border-white/20 bg-white/10 hover:bg-white/20"}`}>{name}</button>
                          ))}
                        </div>
                        {dispositionGroup === "callback" && (
                          <div className="mt-3 rounded-xl bg-white/10 p-3">
                            <label htmlFor="call-callback-at" className="block text-sm font-semibold">Callback date and time</label>
                            <input id="call-callback-at" type="datetime-local" required value={callbackAt} onChange={(event) => setCallbackAt(event.target.value)} className="mt-2 w-full rounded-lg bg-white px-3 py-2 text-charcoal" />
                            <button onClick={() => void disposition("callback_requested", "callback")} disabled={!callbackAt || callActionPending} className="mt-2 w-full rounded-lg bg-amber px-4 py-3 font-bold text-charcoal disabled:opacity-40">Save callback</button>
                          </div>
                        )}
                        {dispositionGroup && dispositionGroup !== "callback" && (
                          <div className="mt-3 flex flex-wrap gap-2" aria-label="Detailed outcome">
                            {(SECONDARY_DISPOSITIONS[dispositionGroup] || []).map(([value, name]) => (
                              <button key={value} disabled={callActionPending} onClick={() => void disposition(value, dispositionGroup)} className="rounded-lg bg-white/10 px-4 py-3 text-sm font-semibold hover:bg-white/20 disabled:opacity-40">{name}</button>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
                    <label className="text-xs font-semibold text-dusk">Task type<select aria-label="Task type" value={standaloneTaskType} onChange={(event) => setStandaloneTaskType(event.target.value)} className="mt-1 block w-full rounded-lg border border-stone bg-white px-3 py-2 text-sm text-charcoal"><option value="call">Call</option><option value="email">Email</option><option value="follow_up">Follow up</option><option value="meeting">Meeting</option><option value="general">General</option></select></label>
                    <label className="text-xs font-semibold text-dusk">Task title<input aria-label="Task title" value={standaloneTaskTitle} onChange={(event) => setStandaloneTaskTitle(event.target.value)} placeholder={`${label(standaloneTaskType)}: ${contactName(selected)}`} className="mt-1 block w-full rounded-lg border border-stone bg-white px-3 py-2 text-sm text-charcoal" /></label>
                    <label className="text-xs font-semibold text-dusk">Due date and time<input type="datetime-local" value={standaloneCallbackAt} onChange={(event) => setStandaloneCallbackAt(event.target.value)} className="mt-1 block w-full rounded-lg border border-stone bg-white px-3 py-2 text-sm text-charcoal" /></label>
                    <label className="text-xs font-semibold text-dusk">Priority<select aria-label="Task priority" value={standaloneTaskPriority} onChange={(event) => setStandaloneTaskPriority(event.target.value)} className="mt-1 block w-full rounded-lg border border-stone bg-white px-3 py-2 text-sm text-charcoal"><option value="low">Low</option><option value="normal">Normal</option><option value="high">High</option></select></label>
                    <button
                      onClick={() => void createTask()}
                      disabled={!standaloneCallbackAt || (standaloneTaskType === "call" && !readiness.ready)}
                      title={standaloneTaskType !== "call" || readiness.ready ? "Schedule task" : "Resolve the calling restriction first"}
                      className="rounded-lg border border-stone bg-white px-4 py-2 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-45 sm:col-span-2 lg:col-span-4"
                    >
                      Schedule task
                    </button>
                  </div>
                  <form onSubmit={addNote} className="mt-4 flex gap-2"><label htmlFor="crm-note" className="sr-only">Add note</label><input id="crm-note" value={note} onChange={(event) => setNote(event.target.value)} placeholder="Add a short factual note…" className="min-w-0 flex-1 rounded-lg border border-stone bg-white px-3 py-2 text-sm" /><button className="rounded-lg bg-bark px-4 py-2 text-sm font-semibold text-white">Save note</button></form>
                  <div className="mt-6"><h3 className="text-lg font-bold">Activity</h3><div className="mt-3 max-h-64 space-y-3 overflow-y-auto">{timeline.map((activity) => <div key={activity.id} className="border-l-2 border-stone pl-3 text-sm"><div className="font-semibold text-charcoal">{label(activity.activity_type)}</div>{activity.body && <div className="mt-1 text-dusk">{activity.body}</div>}<div className="mt-1 text-xs text-dusk">{new Date(activity.created_at).toLocaleString("en-GB")}</div></div>)}{!timeline.length && <p className="text-sm text-dusk">No activity recorded yet.</p>}</div></div>
                </>
              )}
            </section>

            <aside className="space-y-4">
              <form onSubmit={createContact} aria-label="Add contact" className="rounded-2xl border border-stone bg-cream p-4"><h2 className="text-xl font-bold">Add contact</h2><p className="mt-1 text-xs text-dusk">CareGist checks the local TPS/CTPS cache automatically.</p><div className="mt-4 space-y-2"><input aria-label="CQC location ID" name="provider_id" maxLength={20} placeholder="CQC location ID (optional)" className="w-full rounded-lg border border-stone bg-white px-3 py-2 text-sm" /><div className="grid grid-cols-2 gap-2"><input aria-label="First name" name="first_name" maxLength={120} placeholder="First name" className="w-full rounded-lg border border-stone bg-white px-3 py-2 text-sm" /><input aria-label="Last name" name="last_name" maxLength={120} placeholder="Last name" className="w-full rounded-lg border border-stone bg-white px-3 py-2 text-sm" /></div><select aria-label="Saved company" name="company_id" className="w-full rounded-lg border border-stone bg-white px-3 py-2 text-sm"><option value="">No saved company</option>{summary?.companies.map((company) => <option key={company.id} value={company.id}>{company.name}</option>)}</select><input aria-label="New company name" name="company_name" maxLength={255} placeholder="Or add company name" className="w-full rounded-lg border border-stone bg-white px-3 py-2 text-sm" /><input aria-label="Email address" name="email" type="email" placeholder="Email" className="w-full rounded-lg border border-stone bg-white px-3 py-2 text-sm" /><input aria-label="Telephone number" name="phone_e164" placeholder="+442071234567" className="w-full rounded-lg border border-stone bg-white px-3 py-2 text-sm" /><button disabled={busy} className="w-full rounded-lg bg-bark px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">Add to CRM</button></div></form>
              <form onSubmit={createCompany} aria-label="Add company" className="rounded-2xl border border-stone bg-cream p-4"><h2 className="text-xl font-bold">Add company</h2><div className="mt-4 space-y-2"><input aria-label="Company name" required name="name" maxLength={255} placeholder="Company name" className="w-full rounded-lg border border-stone bg-white px-3 py-2 text-sm" /><input aria-label="Company website" name="website" type="url" maxLength={500} placeholder="https://example.co.uk" className="w-full rounded-lg border border-stone bg-white px-3 py-2 text-sm" /><input aria-label="Company telephone number" name="phone_e164" placeholder="+442071234567" className="w-full rounded-lg border border-stone bg-white px-3 py-2 text-sm" /><input aria-label="Business address" name="address" maxLength={2000} placeholder="Business address" className="w-full rounded-lg border border-stone bg-white px-3 py-2 text-sm" /><button className="w-full rounded-lg border border-bark bg-white px-4 py-2 text-sm font-semibold text-bark">Save company</button></div></form>
              <div className="rounded-2xl border border-stone bg-cream p-4"><h2 className="text-xl font-bold">Next tasks</h2><div className="mt-3 max-h-80 space-y-2 overflow-y-auto">{summary?.tasks.map((task) => <div key={task.id} className="rounded-xl border border-stone bg-white p-3"><button disabled={Boolean(callSessionId) && selectedId !== task.contact_id} onClick={() => setSelectedId(task.contact_id)} className="w-full text-left disabled:cursor-not-allowed disabled:opacity-40"><div className="text-xs font-semibold uppercase tracking-wider text-clay">{label(task.task_type)} · {task.priority}</div><div className="mt-1 text-sm font-semibold">{task.title}</div><div className="mt-1 text-xs text-dusk">{new Date(task.due_at).toLocaleString("en-GB")}</div></button><button onClick={() => void completeTask(task.id)} className="mt-2 text-xs font-bold text-moss">Mark complete</button></div>)}{!summary?.tasks.length && <p className="py-4 text-center text-sm text-dusk">No open tasks.</p>}</div></div>
            </aside>
          </div>
        )}

        {tab === "pipeline" && (
          <div className="grid gap-4 lg:grid-cols-[360px_minmax(0,1fr)]">
            <div className="rounded-2xl border border-stone bg-cream p-5"><h2 className="text-2xl font-bold">Add a deal</h2><p className="mt-1 text-sm text-dusk">Choose a contact in the call queue first.</p><div className="mt-4 rounded-xl bg-parchment p-3 font-semibold">{selected ? contactName(selected) : "No contact selected"}</div><form onSubmit={createDeal} aria-label="Add deal" className="mt-4 space-y-3"><input aria-label="Deal title" required name="title" maxLength={255} placeholder="Deal title" className="w-full rounded-lg border border-stone bg-white px-3 py-2" /><input aria-label="Deal value in pounds" required name="value_gbp" type="number" min="0" max="1000000" step="0.01" placeholder="Value in £" className="w-full rounded-lg border border-stone bg-white px-3 py-2" /><button disabled={!selected} className="w-full rounded-lg bg-bark px-4 py-2 font-semibold text-white disabled:opacity-40">Add deal</button></form></div>
            <div className="overflow-hidden rounded-2xl border border-stone bg-cream">
              <div className="border-b border-stone p-5"><h2 className="text-2xl font-bold">Sales pipeline</h2><p className="mt-1 text-sm text-dusk">Move each deal with the simple stage menu.</p></div>
              {pendingLostDeal && <form onSubmit={(event) => { event.preventDefault(); void saveDealStage(pendingLostDeal, "lost", lossReason.trim()); }} className="m-4 rounded-xl border border-alert/30 bg-white p-4"><label htmlFor="loss-reason" className="text-sm font-semibold">Why was {pendingLostDeal.title} lost?</label><textarea id="loss-reason" required maxLength={2000} value={lossReason} onChange={(event) => setLossReason(event.target.value)} className="mt-2 w-full rounded-lg border border-stone p-3" /><div className="mt-2 flex gap-2"><button disabled={!lossReason.trim()} className="rounded-lg bg-bark px-4 py-2 text-sm font-semibold text-white disabled:opacity-40">Save lost reason</button><button type="button" onClick={() => { setPendingLostDeal(null); setLossReason(""); }} className="rounded-lg border border-stone px-4 py-2 text-sm font-semibold">Cancel</button></div></form>}
              <div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm"><thead className="bg-parchment text-xs uppercase tracking-wider text-dusk"><tr><th scope="col" className="p-3">Deal</th><th scope="col" className="p-3">Contact</th><th scope="col" className="p-3">Value</th><th scope="col" className="p-3">Stage</th><th scope="col" className="p-3">Updated</th></tr></thead><tbody>{summary?.deals.map((deal) => <tr key={deal.id} className="border-t border-stone"><td className="p-3 font-semibold">{deal.title}</td><td className="p-3">{deal.provider_name || deal.company_name || `${deal.first_name} ${deal.last_name}`}</td><td className="p-3">{pounds(deal.value_pence)}</td><td className="p-3"><select aria-label={`Stage for ${deal.title}`} value={deal.stage} onChange={(event) => void changeDealStage(deal, event.target.value)} className="rounded-lg border border-stone bg-white px-2 py-1.5">{STAGES.map((stage) => <option key={stage} value={stage}>{label(stage)}</option>)}</select></td><td className="p-3 text-dusk">{new Date(deal.updated_at).toLocaleDateString("en-GB")}</td></tr>)}{!summary?.deals.length && <tr><td colSpan={5} className="p-10 text-center text-dusk">No deals yet.</td></tr>}</tbody></table></div>
            </div>
          </div>
        )}

        {tab === "campaigns" && (
          !summary?.features.email_campaigns_enabled ? <div className="rounded-2xl border border-stone bg-cream p-8 text-center"><h2 className="text-2xl font-bold">Email campaigns are safely locked</h2><p className="mt-2 text-dusk">Configure Resend, its signed webhook and the public sender address before enabling this feature.</p></div> : !manager ? <div className="rounded-2xl border border-stone bg-cream p-8 text-center">Only a CRM owner or administrator can send campaigns.</div> : (
            <div className="grid gap-4 xl:grid-cols-[420px_minmax(0,1fr)]">
              <div className="rounded-2xl border border-stone bg-cream p-5"><h2 className="text-2xl font-bold">Create email</h2><p className="mt-1 text-sm text-dusk">CareGist adds the unsubscribe link and blocks ineligible contacts.</p><form onSubmit={createCampaign} aria-label="Create email campaign" className="mt-4 space-y-3"><input aria-label="Internal campaign name" required name="name" maxLength={160} placeholder="Internal campaign name" className="w-full rounded-lg border border-stone bg-white px-3 py-2" /><input aria-label="Email subject" required name="subject" maxLength={500} placeholder="Email subject" className="w-full rounded-lg border border-stone bg-white px-3 py-2" /><textarea aria-label="Email body" required name="body_text" maxLength={20000} rows={8} placeholder="Write the email in plain language…" className="w-full rounded-lg border border-stone bg-white px-3 py-2" /><button className="w-full rounded-lg bg-bark px-4 py-2 font-semibold text-white">Create safe draft</button></form>{campaignDraftId && <div className="mt-5 rounded-xl border border-sage bg-white p-4"><h3 className="font-bold">Choose recipients</h3><p className="mt-1 text-xs text-dusk">Only contacts with a recorded UK email basis appear.</p><div className="mt-3 max-h-56 space-y-2 overflow-y-auto">{eligibleEmailContacts.map((contact) => <label key={contact.id} className="flex cursor-pointer items-center gap-2 rounded-lg border border-stone p-2"><input type="checkbox" checked={recipientIds.includes(contact.id)} onChange={(event) => setRecipientIds((current) => event.target.checked ? [...current, contact.id] : current.filter((id) => id !== contact.id))} /><span className="text-sm">{contactName(contact)} · {contact.email}</span></label>)}{!eligibleEmailContacts.length && <p className="text-sm text-dusk">No eligible recipients. Record email permission in Safety first.</p>}</div><label className="mt-4 flex items-start gap-2 text-sm"><input className="mt-1" type="checkbox" checked={confirmCampaign} onChange={(event) => setConfirmCampaign(event.target.checked)} /><span>I checked the message and confirm these recipients may receive it.</span></label><button onClick={() => void launchCampaign()} disabled={!confirmCampaign || recipientIds.length === 0 || busy} className="mt-3 w-full rounded-lg bg-moss px-4 py-2 font-bold text-white disabled:opacity-40">Queue {recipientIds.length} email{recipientIds.length === 1 ? "" : "s"}</button></div>}</div>
              <div className="overflow-hidden rounded-2xl border border-stone bg-cream"><div className="border-b border-stone p-5"><h2 className="text-2xl font-bold">Campaign results</h2></div><div className="overflow-x-auto"><table className="w-full min-w-[980px] text-left text-sm"><thead className="bg-parchment text-xs uppercase tracking-wider text-dusk"><tr><th scope="col" className="p-3">Campaign</th><th scope="col" className="p-3">Status</th><th scope="col" className="p-3">Recipients</th><th scope="col" className="p-3">Failed</th><th scope="col" className="p-3">Delivered</th><th scope="col" className="p-3">Bounced</th><th scope="col" className="p-3">Complaints</th><th scope="col" className="p-3">Unsubscribed</th></tr></thead><tbody>{campaigns.map((campaign) => <tr key={campaign.id} className="border-t border-stone"><td className="p-3"><div className="font-semibold">{campaign.name}</div><div className="text-xs text-dusk">{campaign.subject}</div></td><td className="p-3">{label(campaign.status)}</td><td className="p-3">{campaign.recipient_count}</td><td className="p-3">{campaign.failed_count}</td><td className="p-3">{campaign.delivered_count}</td><td className="p-3">{campaign.bounced_count}</td><td className="p-3">{campaign.complained_count}</td><td className="p-3">{campaign.unsubscribed_count}</td></tr>)}{!campaigns.length && <tr><td colSpan={8} className="p-10 text-center text-dusk">No campaigns yet.</td></tr>}</tbody></table></div></div>
            </div>
          )
        )}

        {tab === "reports" && manager && report && (
          <div className="mb-4 grid gap-4 lg:grid-cols-2">
            <section aria-labelledby="disposition-report-title" className="rounded-2xl border border-stone bg-cream p-5">
              <h2 id="disposition-report-title" className="text-xl font-bold">Disposition report</h2>
              <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
                {report.dispositions.map((item) => <div key={item.outcome} className="rounded-xl bg-parchment p-3"><div className="text-xs text-dusk">{label(item.outcome)}</div><div className="mt-1 text-2xl font-semibold">{item.count}</div></div>)}
                {!report.dispositions.length && <p className="col-span-full text-sm text-dusk">No dispositions in this period.</p>}
              </div>
            </section>
            <section aria-labelledby="campaign-report-title" className="rounded-2xl border border-stone bg-cream p-5">
              <h2 id="campaign-report-title" className="text-xl font-bold">Campaign report</h2>
              <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
                {Object.entries(report.campaigns).map(([name, value]) => <div key={name} className="rounded-xl bg-parchment p-3"><div className="text-xs text-dusk">{label(name)}</div><div className="mt-1 text-2xl font-semibold">{value}</div></div>)}
              </div>
            </section>
          </div>
        )}

        {tab === "reports" && manager && callDetail?.evaluation && (
          <section aria-labelledby="ai-review-title" className="mb-4 rounded-2xl border border-stone bg-cream p-5">
            <h2 id="ai-review-title" className="text-xl font-bold">AI review details <span className="text-sm font-normal text-dusk">· advisory</span></h2>
            <div className="mt-3 grid gap-2 sm:grid-cols-3">
              <div className="rounded-xl bg-parchment p-3"><div className="text-xs text-dusk">Suggested disposition</div><div className="mt-1 font-semibold">{callDetail.evaluation.suggested_disposition ? label(callDetail.evaluation.suggested_disposition) : "—"}</div></div>
              <div className="rounded-xl bg-parchment p-3"><div className="text-xs text-dusk">Customer sentiment</div><div className="mt-1 font-semibold">{callDetail.evaluation.customer_sentiment ? label(callDetail.evaluation.customer_sentiment) : "—"}</div></div>
              <div className="rounded-xl bg-parchment p-3"><div className="text-xs text-dusk">AI outcome</div><div className="mt-1 font-semibold">{callDetail.evaluation.outcome ? label(callDetail.evaluation.outcome) : "—"}</div></div>
            </div>
            <div className="mt-3 rounded-xl border border-alert/30 bg-white p-4"><h3 className="font-bold">Compliance flags</h3>{callDetail.evaluation.compliance_flags?.length ? <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-dusk">{callDetail.evaluation.compliance_flags.map((item) => <li key={item}>{item}</li>)}</ul> : <p className="mt-2 text-sm text-dusk">No compliance flags reported.</p>}</div>
          </section>
        )}

        {tab === "reports" && (
          !manager ? <div className="rounded-2xl border border-stone bg-cream p-8 text-center">Only a CRM owner or administrator can view team performance.</div> : (
            <div className="space-y-4">
              <div className="rounded-2xl border border-stone bg-cream p-5"><div className="flex items-center justify-between"><div><h2 className="text-2xl font-bold">Team performance</h2><p className="mt-1 text-sm text-dusk">Last 30 days · AI scores are advisory coaching aids only.</p></div><button onClick={() => void loadReport()} className="rounded-lg border border-stone bg-white px-4 py-2 text-sm font-semibold">Refresh</button></div><div className="mt-4 overflow-x-auto"><table className="w-full min-w-[800px] text-left text-sm"><thead className="bg-parchment text-xs uppercase tracking-wider text-dusk"><tr><th className="p-3">Agent</th><th className="p-3">Calls</th><th className="p-3">Connected</th><th className="p-3">Talk time</th><th className="p-3">Outcomes saved</th><th className="p-3">Positive</th><th className="p-3">QA score</th></tr></thead><tbody>{report?.agents.map((agent) => <tr key={agent.agent_user_id} className="border-t border-stone"><td className="p-3 font-semibold">{agent.agent}</td><td className="p-3">{agent.calls}</td><td className="p-3">{agent.connected_calls}</td><td className="p-3">{Math.round(agent.talk_seconds / 60)} min</td><td className="p-3">{agent.dispositioned_calls}</td><td className="p-3">{agent.positive_outcomes}</td><td className="p-3">{agent.average_qa_score ?? "—"}</td></tr>)}{!report?.agents.length && <tr><td colSpan={7} className="p-8 text-center text-dusk">No call data in this period.</td></tr>}</tbody></table></div></div>
              <div className="grid gap-4 xl:grid-cols-[420px_minmax(0,1fr)]"><div className="rounded-2xl border border-stone bg-cream p-5"><h2 className="text-xl font-bold">Recent calls</h2><div className="mt-3 max-h-[560px] space-y-2 overflow-y-auto">{summary?.recent_calls.map((call) => <button key={call.id} onClick={() => void loadCallDetail(call.id)} className="w-full rounded-xl border border-stone bg-white p-3 text-left"><div className="flex justify-between gap-2"><span className="font-semibold">{call.provider_name || call.company_name || `${call.first_name} ${call.last_name}`}</span><span className="text-xs text-dusk">{call.duration_seconds || 0}s</span></div><div className="mt-1 text-xs text-dusk">{call.agent} · {label(call.disposition || call.status)}</div><div className="mt-2 flex gap-2 text-[10px] font-bold uppercase tracking-wider"><span>{call.recording_status ? `Recording ${call.recording_status}` : "No recording"}</span><span>·</span><span>{call.intelligence_status ? `AI ${call.intelligence_status}` : "No AI"}</span></div></button>)}{!summary?.recent_calls.length && <p className="py-6 text-center text-sm text-dusk">No calls yet.</p>}</div></div><div className="rounded-2xl border border-stone bg-cream p-5">{!callDetail ? <div className="flex min-h-72 items-center justify-center text-dusk">Choose a recent call to see its recording, transcript and evaluation.</div> : <div><div className="flex flex-wrap items-center justify-between gap-3"><h2 className="text-2xl font-bold">Call review</h2>{callDetail.recording_id && callDetail.recording_status === "ready" && <a href={`/api/v1/crm/recordings/${callDetail.recording_id}/playback`} target="_blank" rel="noreferrer" className="rounded-lg bg-bark px-4 py-2 text-sm font-semibold text-white">Play recording</a>}</div><div className="mt-4 grid grid-cols-3 gap-2"><div className="rounded-xl bg-parchment p-3"><div className="text-xs text-dusk">Outcome</div><div className="mt-1 font-semibold">{label(callDetail.disposition || callDetail.status)}</div></div><div className="rounded-xl bg-parchment p-3"><div className="text-xs text-dusk">Duration</div><div className="mt-1 font-semibold">{callDetail.duration_seconds || 0}s</div></div><div className="rounded-xl bg-parchment p-3"><div className="text-xs text-dusk">QA</div><div className="mt-1 font-semibold">{callDetail.evaluation?.overall_qa_score ?? callDetail.evaluation?.overall_score ?? "—"}</div></div></div>{callDetail.summary && <div className="mt-4 rounded-xl border border-sage bg-white p-4"><div className="text-xs font-bold uppercase tracking-wider text-moss">AI summary · advisory</div><p className="mt-2 text-sm">{callDetail.summary}</p></div>}{callDetail.evaluation && <div className="mt-4 grid gap-3 md:grid-cols-2"><div className="rounded-xl bg-white p-4"><h3 className="font-bold">Strengths</h3><ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-dusk">{(callDetail.evaluation.strengths || []).map((item) => <li key={item}>{item}</li>)}</ul></div><div className="rounded-xl bg-white p-4"><h3 className="font-bold">Coaching actions</h3><ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-dusk">{(callDetail.evaluation.coaching_actions || []).map((item) => <li key={item}>{item}</li>)}</ul></div></div>}{callDetail.transcript && <details className="mt-4 rounded-xl bg-white p-4"><summary className="cursor-pointer font-bold">Transcript</summary><p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-dusk">{callDetail.transcript}</p></details>}{callDetail.intelligence_status === "purged" && <p className="mt-4 text-sm text-dusk">The transcript and evaluation were deleted with the 30-day retention cycle.</p>}</div>}</div></div>
            </div>
          )
        )}

        {tab === "compliance" && (
          !manager ? <div className="rounded-2xl border border-stone bg-cream p-8 text-center"><h2 className="text-2xl font-bold">Safety is automatic</h2><p className="mt-2 text-dusk">Agents do not need to manage TPS/CTPS files or legal evidence. The green, amber and red call status is authoritative.</p></div> : (
            <div className="grid gap-4 xl:grid-cols-3">
              <form onSubmit={importScreening} aria-label="Import TPS and CTPS results" className="rounded-2xl border border-stone bg-cream p-5"><h2 className="text-2xl font-bold">Import TPS/CTPS results</h2><p className="mt-2 text-sm text-dusk">Upload once; CareGist updates every matching lead and the private lookup cache.</p><div className="mt-4 space-y-3"><select aria-label="Screening source" name="source" className="w-full rounded-lg border border-stone bg-white px-3 py-2"><option value="tps_ctps_licence">Official TPS/CTPS licence</option><option value="approved_provider">Approved screening provider</option></select><input aria-label="Screening source reference" required name="source_reference" maxLength={500} placeholder="Licence, batch or download reference" className="w-full rounded-lg border border-stone bg-white px-3 py-2" /><label className="block rounded-xl border-2 border-dashed border-stone bg-white p-5 text-center text-sm"><span className="font-semibold">Choose screening CSV</span><input required name="upload" type="file" accept=".csv,text/csv" className="mt-3 block w-full text-xs" /></label><div className="rounded-lg bg-parchment p-3 text-xs text-dusk"><strong>Required columns:</strong> phone_e164, status, screened_at. Status must be clear, tps or ctps.</div><button disabled={busy} className="w-full rounded-lg bg-bark px-4 py-2 font-bold text-white disabled:opacity-40">Check all matching leads</button></div></form>
              <div className="rounded-2xl border border-stone bg-cream p-5"><h2 className="text-2xl font-bold">Check one contact</h2><p className="mt-2 text-sm text-dusk">Use this only when you have auditable evidence for the selected contact.</p><div className="mt-4 rounded-xl bg-parchment p-3 font-semibold">{selected ? contactName(selected) : "Choose a contact in Call queue"}</div><form onSubmit={recordScreening} aria-label="Record contact screening" className="mt-4 space-y-3"><select aria-label="Screening status" name="status" className="w-full rounded-lg border border-stone bg-white px-3 py-2"><option value="clear">Clear to call</option><option value="tps">On TPS</option><option value="ctps">On CTPS</option><option value="consent_override">Specific consent to CareGist</option></select><select aria-label="Screening evidence source" name="source" className="w-full rounded-lg border border-stone bg-white px-3 py-2"><option value="tps_ctps_licence">Official TPS/CTPS check</option><option value="approved_provider">Approved provider check</option><option value="specific_consent">Specific consent evidence</option></select><input aria-label="Screening evidence reference" required name="reference" maxLength={500} placeholder="Evidence or source reference" className="w-full rounded-lg border border-stone bg-white px-3 py-2" /><button disabled={!selected} className="w-full rounded-lg bg-bark px-4 py-2 font-bold text-white disabled:opacity-40">Save screening</button></form></div>
              <div className="rounded-2xl border border-stone bg-cream p-5"><h2 className="text-2xl font-bold">Email permission</h2><p className="mt-2 text-sm text-dusk">Only eligible contacts can appear in the campaign recipient list.</p><div className="mt-4 rounded-xl bg-parchment p-3 font-semibold">{selected ? contactName(selected) : "Choose a contact in Call queue"}</div><form onSubmit={updateMarketing} aria-label="Record email permission" className="mt-4 space-y-3"><select aria-label="Subscriber type" name="subscriber_type" defaultValue={selected?.subscriber_type || "unknown"} key={`subscriber-${selected?.id}`} className="w-full rounded-lg border border-stone bg-white px-3 py-2"><option value="corporate">Corporate subscriber</option><option value="sole_trader">Sole trader</option><option value="partnership">Partnership</option><option value="individual">Individual</option><option value="unknown">Unknown</option></select><select aria-label="Email marketing basis" name="basis" defaultValue={selected?.email_marketing_basis || "none"} key={`basis-${selected?.id}`} className="w-full rounded-lg border border-stone bg-white px-3 py-2"><option value="none">No marketing permission</option><option value="corporate_subscriber">Corporate B2B</option><option value="consent">Consent</option><option value="soft_opt_in">Soft opt-in</option></select><input aria-label="Email permission evidence reference" name="reference" maxLength={500} placeholder="Consent or source reference" className="w-full rounded-lg border border-stone bg-white px-3 py-2" /><button disabled={!selected} className="w-full rounded-lg bg-bark px-4 py-2 font-bold text-white disabled:opacity-40">Save email permission</button></form><div className="mt-5 rounded-xl border border-alert/30 bg-white p-3 text-xs text-dusk"><strong>Fixed UK rules:</strong> SMS is disabled. Suppression always wins. Recording and AI cannot activate without their independent safety gates.</div></div>
            </div>
          )
        )}
      </div>
    </div>
  );
}
