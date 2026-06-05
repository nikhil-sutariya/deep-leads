"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { Campaign, CampaignEmail, CampaignMetrics } from "@/lib/types";
import CampaignStatusBadge from "@/components/CampaignStatusBadge";

export default function CampaignDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [emails, setEmails] = useState<CampaignEmail[]>([]);
  const [metrics, setMetrics] = useState<CampaignMetrics | null>(null);
  const [selectedEmail, setSelectedEmail] = useState<CampaignEmail | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionMsg, setActionMsg] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    const [campRes, emailsRes] = await Promise.all([
      api.get<{ campaign: Campaign }>(`/campaigns/${params.id}`),
      api.get<{ emails: CampaignEmail[]; total: number }>(`/campaigns/${params.id}/emails`),
    ]);
    setCampaign(campRes.data.campaign);
    setEmails(emailsRes.data.emails);
    if (emailsRes.data.emails.length) {
      setSelectedEmail((prev) => prev ?? emailsRes.data.emails[0]);
    }
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

  async function handleSend() {
    setBusy(true);
    setActionMsg("");
    try {
      const res = await api.post<{ message: string; note?: string }>(`/campaigns/${params.id}/send`);
      setActionMsg(`${res.data.message} ${res.data.note || ""}`);
      await load();
    } catch (e: unknown) {
      setActionMsg("Send failed");
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
    if (!window.confirm(`Delete campaign "${campaign.name}"? This cannot be undone.`)) {
      return;
    }
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
      const res = await api.post<CampaignEmail>(
        `/campaigns/${params.id}/emails/${emailId}/regenerate`
      );
      setEmails((prev) => prev.map((e) => (e.id === emailId ? res.data : e)));
      setSelectedEmail(res.data);
      setActionMsg("Email regenerated");
    } catch {
      setActionMsg("Regenerate failed");
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!campaign) {
    return <p className="text-[#64748b]">Campaign not found</p>;
  }

  return (
    <div className="space-y-5">
      <div>
        <Link href="/campaigns" className="text-sm text-indigo-400 hover:underline">
          ← Back to campaigns
        </Link>
        <div className="flex items-start justify-between mt-2 gap-4">
          <div>
            <h1 className="text-2xl font-semibold text-white">{campaign.name}</h1>
            <div className="flex items-center gap-2 mt-2">
              <CampaignStatusBadge status={campaign.status} />
              <span className="text-sm text-[#64748b]">
                {campaign.total_leads} leads · {campaign.emails_sent} sent
              </span>
            </div>
            {campaign.campaign_goal && (
              <p className="text-sm text-[#94a3b8] mt-3 max-w-2xl">{campaign.campaign_goal}</p>
            )}
          </div>
          <div className="flex gap-2 flex-shrink-0">
            <button
              onClick={handleDelete}
              disabled={busy || campaign.status === "running"}
              title={campaign.status === "running" ? "Pause before deleting" : undefined}
              className="cursor-pointer border border-red-500/40 text-red-400 hover:bg-red-500/10 disabled:opacity-40 disabled:cursor-not-allowed text-sm px-4 py-2 rounded-lg"
            >
              Delete
            </button>
            {campaign.status === "draft" && (
              <button
                onClick={handleSend}
                disabled={busy}
                className="cursor-pointer bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white text-sm px-4 py-2 rounded-lg"
              >
                Send campaign
              </button>
            )}
            {campaign.status === "running" && (
              <button
                onClick={handlePause}
                className="cursor-pointer border border-[#334155] text-[#94a3b8] hover:text-white text-sm px-4 py-2 rounded-lg"
              >
                Pause
              </button>
            )}
            {campaign.status === "paused" && (
              <button
                onClick={handleResume}
                className="cursor-pointer bg-indigo-500 hover:bg-indigo-600 text-white text-sm px-4 py-2 rounded-lg"
              >
                Resume
              </button>
            )}
          </div>
        </div>
      </div>

      {actionMsg && (
        <div className="bg-indigo-500/10 border border-indigo-500/30 rounded-lg px-4 py-3 text-sm text-indigo-300">
          {actionMsg}
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
            <div key={m.label} className="bg-[#1e293b] border border-[#334155] rounded-xl p-4">
              <p className="text-xs text-[#64748b]">{m.label}</p>
              <p className="text-xl font-semibold text-white mt-1">{m.value}</p>
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-1 bg-[#1e293b] border border-[#334155] rounded-xl overflow-hidden max-h-[32rem] overflow-y-auto">
          <div className="p-4 border-b border-[#334155] text-sm font-medium text-[#94a3b8]">
            Emails ({emails.length})
          </div>
          <div className="divide-y divide-[#334155]">
            {emails.map((email) => (
              <button
                key={email.id}
                type="button"
                onClick={() => setSelectedEmail(email)}
                className={`cursor-pointer w-full text-left px-4 py-3 hover:bg-[#334155]/40 transition ${
                  selectedEmail?.id === email.id ? "bg-indigo-500/10 border-l-2 border-indigo-500" : ""
                }`}
              >
                <p className="text-sm font-medium text-white truncate">
                  {email.lead_name || email.recipient_email}
                </p>
                <p className="text-xs text-[#64748b] truncate mt-0.5">{email.subject}</p>
                <div className="flex gap-2 mt-1 text-xs text-[#475569]">
                  {email.sent_at && <span>Sent</span>}
                  {email.opened_at && <span className="text-emerald-400">Opened</span>}
                  {email.follow_up_number > 0 && <span>FU #{email.follow_up_number}</span>}
                </div>
              </button>
            ))}
          </div>
        </div>

        <div className="lg:col-span-2 bg-[#1e293b] border border-[#334155] rounded-xl p-5">
          {selectedEmail ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-[#64748b]">To</p>
                  <p className="text-sm text-white">
                    {selectedEmail.recipient_name
                      ? `${selectedEmail.recipient_name} <${selectedEmail.recipient_email}>`
                      : selectedEmail.recipient_email}
                  </p>
                </div>
                {!selectedEmail.sent_at && (
                  <button
                    onClick={() => handleRegenerate(selectedEmail.id)}
                    disabled={busy}
                    className="cursor-pointer text-xs text-indigo-400 hover:underline disabled:opacity-50"
                  >
                    Regenerate with AI
                  </button>
                )}
              </div>
              <div>
                <p className="text-xs text-[#64748b] mb-1">Subject</p>
                <p className="text-sm text-white font-medium">{selectedEmail.subject}</p>
              </div>
              <div>
                <p className="text-xs text-[#64748b] mb-1">Body</p>
                <pre className="text-sm text-[#cbd5e1] whitespace-pre-wrap font-sans leading-relaxed">
                  {selectedEmail.body}
                </pre>
              </div>
            </div>
          ) : (
            <p className="text-[#64748b] text-sm">Select an email to preview</p>
          )}
        </div>
      </div>
    </div>
  );
}
