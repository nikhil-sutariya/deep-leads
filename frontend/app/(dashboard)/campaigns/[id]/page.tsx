"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { Campaign, CampaignAttachment, CampaignEmail, CampaignMetrics, CampaignSchedulePayload } from "@/lib/types";
import CampaignStatusBadge from "@/components/CampaignStatusBadge";
import { TIMEZONES, DEFAULT_TIMEZONE } from "@/lib/timezones";

function fmtBytes(n?: number) {
  if (!n) return "";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

export default function CampaignDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [emails, setEmails] = useState<CampaignEmail[]>([]);
  const [metrics, setMetrics] = useState<CampaignMetrics | null>(null);
  const [attachments, setAttachments] = useState<CampaignAttachment[]>([]);
  const [selectedEmailId, setSelectedEmailId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionMsg, setActionMsg] = useState("");
  const [busy, setBusy] = useState(false);

  // Email editing
  const [editing, setEditing] = useState(false);
  const [editSubject, setEditSubject] = useState("");
  const [editBody, setEditBody] = useState("");

  // Scheduling
  const [showSchedule, setShowSchedule] = useState(false);
  const [scheduleLocal, setScheduleLocal] = useState("");
  const [scheduleTz, setScheduleTz] = useState(DEFAULT_TIMEZONE);
  const [minDelay, setMinDelay] = useState(3);
  const [maxDelay, setMaxDelay] = useState(8);

  const campaignFileRef = useRef<HTMLInputElement>(null);
  const emailFileRef = useRef<HTMLInputElement>(null);

  const selectedEmail = useMemo(
    () => emails.find((e) => e.id === selectedEmailId) ?? null,
    [emails, selectedEmailId]
  );
  const campaignWide = attachments.filter((a) => !a.email_id);
  const emailSpecific = attachments.filter((a) => a.email_id === selectedEmailId);

  async function load() {
    const [campRes, emailsRes, attRes] = await Promise.all([
      api.get<{ campaign: Campaign }>(`/campaigns/${params.id}`),
      api.get<{ emails: CampaignEmail[]; total: number }>(`/campaigns/${params.id}/emails`),
      api.get<CampaignAttachment[]>(`/campaigns/${params.id}/attachments`),
    ]);
    setCampaign(campRes.data.campaign);
    setEmails(emailsRes.data.emails);
    setAttachments(attRes.data);
    if (emailsRes.data.emails.length) {
      setSelectedEmailId((prev) => prev ?? emailsRes.data.emails[0].id);
    }
    // Seed scheduling defaults from the campaign.
    if (campRes.data.campaign.send_timezone) setScheduleTz(campRes.data.campaign.send_timezone);
    if (campRes.data.campaign.min_delay_seconds != null) setMinDelay(campRes.data.campaign.min_delay_seconds / 60);
    if (campRes.data.campaign.max_delay_seconds != null) setMaxDelay(campRes.data.campaign.max_delay_seconds / 60);
    if (campRes.data.campaign.emails_sent > 0) {
      try {
        const m = await api.get<CampaignMetrics>(`/campaigns/${params.id}/metrics`);
        setMetrics(m.data);
      } catch {
        setMetrics(null);
      }
    }
  }

  useEffect(() => {
    load()
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [params.id]);

  // Reset the editor whenever the selected email changes.
  useEffect(() => {
    setEditing(false);
    setEditSubject(selectedEmail?.subject ?? "");
    setEditBody(selectedEmail?.body ?? "");
  }, [selectedEmailId, selectedEmail?.subject, selectedEmail?.body]);

  async function refreshAttachments() {
    const res = await api.get<CampaignAttachment[]>(`/campaigns/${params.id}/attachments`);
    setAttachments(res.data);
  }

  async function handleSend() {
    setBusy(true);
    setActionMsg("");
    try {
      const res = await api.post<{ message: string; note?: string }>(`/campaigns/${params.id}/send`);
      setActionMsg(`${res.data.message} ${res.data.note || ""}`);
      await load();
    } catch {
      setActionMsg("Send failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleSchedule() {
    if (!scheduleLocal) {
      setActionMsg("Pick a date and time to schedule");
      return;
    }
    setBusy(true);
    setActionMsg("");
    try {
      const payload: CampaignSchedulePayload = {
        scheduled_local: scheduleLocal,
        send_timezone: scheduleTz,
        min_delay_seconds: Math.round(minDelay * 60),
        max_delay_seconds: Math.round(maxDelay * 60),
      };
      const res = await api.post<{ message: string }>(`/campaigns/${params.id}/schedule`, payload);
      setActionMsg(res.data.message);
      setShowSchedule(false);
      await load();
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Schedule failed";
      setActionMsg(typeof msg === "string" ? msg : "Schedule failed");
    } finally {
      setBusy(false);
    }
  }

  async function handlePause() {
    await api.post(`/campaigns/${params.id}/pause`);
    await load();
  }

  async function handleResume() {
    await api.post(`/campaigns/${params.id}/resume`);
    await load();
  }

  async function handleDelete() {
    if (!campaign) return;
    if (campaign.status === "running") {
      setActionMsg("Pause the campaign before deleting.");
      return;
    }
    if (!window.confirm(`Delete campaign "${campaign.name}"? This cannot be undone.`)) return;
    setBusy(true);
    try {
      await api.delete(`/campaigns/${params.id}`);
      router.push("/campaigns");
    } catch {
      setActionMsg("Delete failed. Pause the campaign if it is still running.");
    } finally {
      setBusy(false);
    }
  }

  async function handleRegenerate(emailId: string) {
    setBusy(true);
    try {
      const res = await api.post<CampaignEmail>(`/campaigns/${params.id}/emails/${emailId}/regenerate`);
      setEmails((prev) => prev.map((e) => (e.id === emailId ? res.data : e)));
      setActionMsg("Email regenerated");
    } catch {
      setActionMsg("Regenerate failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleSaveEmail() {
    if (!selectedEmail) return;
    setBusy(true);
    try {
      const res = await api.patch<CampaignEmail>(
        `/campaigns/${params.id}/emails/${selectedEmail.id}`,
        { subject: editSubject, body: editBody }
      );
      setEmails((prev) => prev.map((e) => (e.id === selectedEmail.id ? res.data : e)));
      setEditing(false);
      setActionMsg("Email saved");
    } catch {
      setActionMsg("Save failed");
    } finally {
      setBusy(false);
    }
  }

  async function uploadAttachment(file: File, emailId?: string) {
    setBusy(true);
    setActionMsg("");
    try {
      const fd = new FormData();
      fd.append("file", file);
      if (emailId) fd.append("email_id", emailId);
      await api.post(`/campaigns/${params.id}/attachments`, fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      await refreshAttachments();
      setActionMsg(`Attached ${file.name}`);
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Upload failed";
      setActionMsg(typeof msg === "string" ? msg : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  async function deleteAttachment(id: string) {
    setBusy(true);
    try {
      await api.delete(`/campaigns/${params.id}/attachments/${id}`);
      await refreshAttachments();
    } catch {
      setActionMsg("Could not delete attachment");
    } finally {
      setBusy(false);
    }
  }

  function downloadUrl(id: string) {
    const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    return `${base}/api/v1/campaigns/${params.id}/attachments/${id}/download`;
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!campaign) {
    return <p className="text-subtle">Campaign not found</p>;
  }

  const canSchedule = ["draft", "scheduled", "paused"].includes(campaign.status);
  const canSendNow = ["draft", "scheduled", "paused"].includes(campaign.status);

  function AttachmentRow({ att, onDelete }: { att: CampaignAttachment; onDelete?: () => void }) {
    return (
      <div className="flex items-center justify-between gap-2 bg-background border border-border rounded-lg px-3 py-2">
        <a
          href={downloadUrl(att.id)}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-foreground truncate hover:text-indigo-400"
          title={att.filename}
        >
          📎 {att.filename}
          <span className="text-xs text-faint ml-2">{fmtBytes(att.size_bytes)}</span>
        </a>
        {onDelete && (
          <button onClick={onDelete} disabled={busy} className="cursor-pointer text-xs text-red-400 hover:underline flex-shrink-0">
            Remove
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div>
        <Link href="/campaigns" className="text-sm text-indigo-400 hover:underline">
          ← Back to campaigns
        </Link>
        <div className="flex items-start justify-between mt-2 gap-4">
          <div>
            <h1 className="text-2xl font-semibold text-foreground">{campaign.name}</h1>
            <div className="flex items-center gap-2 mt-2">
              <CampaignStatusBadge status={campaign.status} />
              <span className="text-sm text-subtle">
                {campaign.total_leads} leads · {campaign.emails_sent} sent
              </span>
            </div>
            {campaign.status === "scheduled" && campaign.scheduled_at && (
              <p className="text-sm text-amber-400 mt-2">
                Scheduled to start {new Date(campaign.scheduled_at).toLocaleString()}
                {campaign.send_timezone ? ` · set in ${campaign.send_timezone}` : ""}
              </p>
            )}
            {campaign.campaign_goal && (
              <p className="text-sm text-muted mt-3 max-w-2xl">{campaign.campaign_goal}</p>
            )}
          </div>
          <div className="flex gap-2 flex-shrink-0 flex-wrap justify-end">
            <button
              onClick={handleDelete}
              disabled={busy || campaign.status === "running"}
              title={campaign.status === "running" ? "Pause before deleting" : undefined}
              className="cursor-pointer border border-red-500/40 text-red-400 hover:bg-red-500/10 disabled:opacity-40 disabled:cursor-not-allowed text-sm px-4 py-2 rounded-lg"
            >
              Delete
            </button>
            {canSchedule && (
              <button
                onClick={() => setShowSchedule((s) => !s)}
                className="cursor-pointer border border-border text-muted hover:text-foreground text-sm px-4 py-2 rounded-lg"
              >
                {campaign.status === "scheduled" ? "Reschedule" : "Schedule"}
              </button>
            )}
            {canSendNow && (
              <button
                onClick={handleSend}
                disabled={busy}
                className="cursor-pointer bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white text-sm px-4 py-2 rounded-lg"
              >
                Send now
              </button>
            )}
            {campaign.status === "running" && (
              <button onClick={handlePause} className="cursor-pointer border border-border text-muted hover:text-foreground text-sm px-4 py-2 rounded-lg">
                Pause
              </button>
            )}
            {campaign.status === "paused" && (
              <button onClick={handleResume} className="cursor-pointer bg-indigo-500 hover:bg-indigo-600 text-white text-sm px-4 py-2 rounded-lg">
                Resume
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Schedule panel */}
      {showSchedule && (
        <div className="bg-card border border-border rounded-xl p-5 space-y-4">
          <h2 className="text-sm font-medium text-muted uppercase tracking-wide">Schedule send</h2>
          <p className="text-xs text-faint -mt-2">
            Sending begins at this wall-clock time in the selected timezone. Emails are paced with a random gap between min and max.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-muted mb-1">Start date &amp; time</label>
              <input
                type="datetime-local"
                value={scheduleLocal}
                onChange={(e) => setScheduleLocal(e.target.value)}
                className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground"
              />
            </div>
            <div>
              <label className="block text-sm text-muted mb-1">Timezone</label>
              <select
                value={scheduleTz}
                onChange={(e) => setScheduleTz(e.target.value)}
                className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground"
              >
                {TIMEZONES.map((tz) => (
                  <option key={tz.value} value={tz.value}>{tz.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm text-muted mb-1">Min delay (minutes)</label>
              <input type="number" min={0} step={0.5} value={minDelay} onChange={(e) => setMinDelay(Number(e.target.value))} className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground" />
            </div>
            <div>
              <label className="block text-sm text-muted mb-1">Max delay (minutes)</label>
              <input type="number" min={0} step={0.5} value={maxDelay} onChange={(e) => setMaxDelay(Number(e.target.value))} className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground" />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button onClick={() => setShowSchedule(false)} className="cursor-pointer text-sm text-muted hover:text-foreground border border-border px-4 py-2 rounded-lg">Cancel</button>
            <button onClick={handleSchedule} disabled={busy} className="cursor-pointer bg-indigo-500 hover:bg-indigo-600 disabled:opacity-50 text-white text-sm px-4 py-2 rounded-lg">Schedule send</button>
          </div>
        </div>
      )}

      {actionMsg && (
        <div className="bg-indigo-500/10 border border-indigo-500/30 rounded-lg px-4 py-3 text-sm text-indigo-300 flex items-center justify-between">
          <span>{actionMsg}</span>
          <button onClick={() => setActionMsg("")} className="text-subtle hover:text-foreground ml-4">✕</button>
        </div>
      )}

      {metrics && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: "Open rate", value: `${metrics.open_rate}%` },
            { label: "Click rate", value: `${metrics.click_rate}%` },
            { label: "Response rate", value: `${metrics.response_rate}%` },
            { label: "Bounce rate", value: `${metrics.bounce_rate}%` },
          ].map((m) => (
            <div key={m.label} className="bg-card border border-border rounded-xl p-4">
              <p className="text-xs text-subtle">{m.label}</p>
              <p className="text-xl font-semibold text-foreground mt-1">{m.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Campaign-wide attachments */}
      <div className="bg-card border border-border rounded-xl p-5 space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-medium text-muted uppercase tracking-wide">Campaign attachments</h2>
            <p className="text-xs text-faint mt-0.5">Sent with every email (e.g. a brochure PDF).</p>
          </div>
          <input
            ref={campaignFileRef}
            type="file"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) uploadAttachment(f);
              e.target.value = "";
            }}
          />
          <button onClick={() => campaignFileRef.current?.click()} disabled={busy} className="cursor-pointer border border-border text-foreground hover:bg-hover text-sm px-3 py-2 rounded-lg disabled:opacity-50">
            + Upload file
          </button>
        </div>
        {campaignWide.length ? (
          <div className="space-y-2">
            {campaignWide.map((att) => (
              <AttachmentRow key={att.id} att={att} onDelete={() => deleteAttachment(att.id)} />
            ))}
          </div>
        ) : (
          <p className="text-sm text-faint">No campaign-wide attachments yet.</p>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-1 bg-card border border-border rounded-xl overflow-hidden max-h-[32rem] overflow-y-auto">
          <div className="p-4 border-b border-border text-sm font-medium text-muted">
            Emails ({emails.length})
          </div>
          <div className="divide-y divide-border">
            {emails.map((email) => (
              <button
                key={email.id}
                type="button"
                onClick={() => setSelectedEmailId(email.id)}
                className={`cursor-pointer w-full text-left px-4 py-3 hover:bg-hover/40 transition ${
                  selectedEmailId === email.id ? "bg-indigo-500/10 border-l-2 border-indigo-500" : ""
                }`}
              >
                <p className="text-sm font-medium text-foreground truncate">
                  {email.lead_name || email.recipient_email}
                </p>
                <p className="text-xs text-subtle truncate mt-0.5">{email.subject}</p>
                <div className="flex gap-2 mt-1 text-xs text-faint">
                  {email.sent_at && <span>Sent</span>}
                  {email.opened_at && <span className="text-emerald-400">Opened</span>}
                  {email.follow_up_number > 0 && <span>FU #{email.follow_up_number}</span>}
                </div>
              </button>
            ))}
          </div>
        </div>

        <div className="lg:col-span-2 bg-card border border-border rounded-xl p-5">
          {selectedEmail ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between gap-2">
                <div className="min-w-0">
                  <p className="text-xs text-subtle">To</p>
                  <p className="text-sm text-foreground truncate">
                    {selectedEmail.recipient_name
                      ? `${selectedEmail.recipient_name} <${selectedEmail.recipient_email}>`
                      : selectedEmail.recipient_email}
                  </p>
                </div>
                {!selectedEmail.sent_at && (
                  <div className="flex items-center gap-3 flex-shrink-0">
                    {editing ? (
                      <>
                        <button onClick={handleSaveEmail} disabled={busy} className="cursor-pointer text-xs text-emerald-400 hover:underline disabled:opacity-50">Save</button>
                        <button onClick={() => { setEditing(false); setEditSubject(selectedEmail.subject ?? ""); setEditBody(selectedEmail.body ?? ""); }} className="cursor-pointer text-xs text-muted hover:underline">Cancel</button>
                      </>
                    ) : (
                      <>
                        <button onClick={() => setEditing(true)} className="cursor-pointer text-xs text-indigo-400 hover:underline">Edit</button>
                        <button onClick={() => handleRegenerate(selectedEmail.id)} disabled={busy} className="cursor-pointer text-xs text-indigo-400 hover:underline disabled:opacity-50">Regenerate with AI</button>
                      </>
                    )}
                  </div>
                )}
              </div>

              <div>
                <p className="text-xs text-subtle mb-1">Subject</p>
                {editing ? (
                  <input value={editSubject} onChange={(e) => setEditSubject(e.target.value)} className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground" />
                ) : (
                  <p className="text-sm text-foreground font-medium">{selectedEmail.subject}</p>
                )}
              </div>

              <div>
                <p className="text-xs text-subtle mb-1">Body</p>
                {editing ? (
                  <textarea value={editBody} onChange={(e) => setEditBody(e.target.value)} rows={12} className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground font-sans leading-relaxed resize-y" />
                ) : (
                  <pre className="text-sm text-foreground whitespace-pre-wrap font-sans leading-relaxed">{selectedEmail.body}</pre>
                )}
              </div>

              {/* Per-email attachments */}
              <div className="border-t border-border pt-4 space-y-2">
                <div className="flex items-center justify-between">
                  <p className="text-xs text-subtle">Attachments for this email</p>
                  {!selectedEmail.sent_at && (
                    <>
                      <input
                        ref={emailFileRef}
                        type="file"
                        className="hidden"
                        onChange={(e) => {
                          const f = e.target.files?.[0];
                          if (f) uploadAttachment(f, selectedEmail.id);
                          e.target.value = "";
                        }}
                      />
                      <button onClick={() => emailFileRef.current?.click()} disabled={busy} className="cursor-pointer text-xs text-indigo-400 hover:underline disabled:opacity-50">+ Add file</button>
                    </>
                  )}
                </div>
                {campaignWide.length > 0 && (
                  <p className="text-xs text-faint">+ {campaignWide.length} campaign-wide attachment(s) also included.</p>
                )}
                {emailSpecific.length ? (
                  <div className="space-y-2">
                    {emailSpecific.map((att) => (
                      <AttachmentRow key={att.id} att={att} onDelete={selectedEmail.sent_at ? undefined : () => deleteAttachment(att.id)} />
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-faint">No email-specific attachments.</p>
                )}
              </div>
            </div>
          ) : (
            <p className="text-subtle text-sm">Select an email to preview</p>
          )}
        </div>
      </div>
    </div>
  );
}
