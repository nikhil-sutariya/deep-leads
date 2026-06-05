"use client";
import { FormEvent, useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { ApiEnvelope, CampaignCreatePayload, Lead, LeadListResponse, LeadStatus } from "@/lib/types";
import StatusBadge from "@/components/StatusBadge";

function NewCampaignForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const preselected = searchParams.get("leads")?.split(",").filter(Boolean) ?? [];

  const [leads, setLeads] = useState<Lead[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set(preselected));
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [statusFilter, setStatusFilter] = useState<LeadStatus | "">("enriched");

  const [name, setName] = useState("");
  const [campaignGoal, setCampaignGoal] = useState("");
  const [subjectLine, setSubjectLine] = useState("Quick idea for {company_name}");
  const [bodyTemplate, setBodyTemplate] = useState(
    "Hi {contact_name},\n\nI noticed {company_name} is doing interesting work in {industry}. I'd love to share how we can help.\n\nWould you be open to a short call next week?\n\nBest,"
  );
  const [fromEmail, setFromEmail] = useState("");
  const [fromName, setFromName] = useState("");
  const [followUpDays, setFollowUpDays] = useState("3,7,14");

  useEffect(() => {
    const params: Record<string, unknown> = { skip: 0, limit: 200 };
    if (statusFilter) params.status = statusFilter;
    api
      .get<ApiEnvelope<LeadListResponse>>("/leads", { params })
      .then((res) => setLeads(res.data.data.leads))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [statusFilter]);

  function toggleLead(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (selected.size === 0) {
      setError("Select at least one lead");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      const days = followUpDays
        .split(",")
        .map((d) => parseInt(d.trim(), 10))
        .filter((n) => !isNaN(n));

      const payload: CampaignCreatePayload = {
        name,
        lead_ids: Array.from(selected),
        campaign_goal: campaignGoal,
        email_template: { subject_line: subjectLine, body: bodyTemplate },
        send_from_email: fromEmail,
        send_from_name: fromName,
        follow_up_days: days.length ? days : undefined,
      };

      const res = await api.post<{ campaign: { id: string }; message: string }>("/campaigns", payload);
      router.push(`/campaigns/${res.data.campaign.id}`);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        "Failed to create campaign";
      setError(typeof msg === "string" ? msg : JSON.stringify(msg));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <Link href="/campaigns" className="text-sm text-indigo-400 hover:underline">
          ← Back to campaigns
        </Link>
        <h1 className="text-2xl font-semibold text-white mt-2">New Campaign</h1>
        <p className="text-sm text-[#64748b] mt-0.5">Select leads and configure AI-personalized outreach</p>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 text-sm text-red-300">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="bg-[#1e293b] border border-[#334155] rounded-xl p-5 space-y-4">
          <h2 className="text-sm font-medium text-[#94a3b8] uppercase tracking-wide">Campaign details</h2>
          <div>
            <label className="block text-sm text-[#94a3b8] mb-1">Campaign name</label>
            <input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full bg-[#0f172a] border border-[#334155] rounded-lg px-3 py-2 text-sm text-white"
              placeholder="Garage Door API - Q2 2026"
            />
          </div>
          <div>
            <label className="block text-sm text-[#94a3b8] mb-1">Campaign goal</label>
            <textarea
              required
              rows={3}
              value={campaignGoal}
              onChange={(e) => setCampaignGoal(e.target.value)}
              className="w-full bg-[#0f172a] border border-[#334155] rounded-lg px-3 py-2 text-sm text-white resize-none"
              placeholder="Introduce our garage door boundary detection API to companies with door visualization tools..."
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-[#94a3b8] mb-1">From email</label>
              <input
                required
                type="email"
                value={fromEmail}
                onChange={(e) => setFromEmail(e.target.value)}
                className="w-full bg-[#0f172a] border border-[#334155] rounded-lg px-3 py-2 text-sm text-white"
              />
            </div>
            <div>
              <label className="block text-sm text-[#94a3b8] mb-1">From name</label>
              <input
                required
                value={fromName}
                onChange={(e) => setFromName(e.target.value)}
                className="w-full bg-[#0f172a] border border-[#334155] rounded-lg px-3 py-2 text-sm text-white"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm text-[#94a3b8] mb-1">Follow-up days (comma-separated)</label>
            <input
              value={followUpDays}
              onChange={(e) => setFollowUpDays(e.target.value)}
              className="w-full bg-[#0f172a] border border-[#334155] rounded-lg px-3 py-2 text-sm text-white"
              placeholder="3,7,14"
            />
          </div>
        </div>

        <div className="bg-[#1e293b] border border-[#334155] rounded-xl p-5 space-y-4">
          <h2 className="text-sm font-medium text-[#94a3b8] uppercase tracking-wide">Email template</h2>
          <div>
            <label className="block text-sm text-[#94a3b8] mb-1">Subject template</label>
            <input
              required
              value={subjectLine}
              onChange={(e) => setSubjectLine(e.target.value)}
              className="w-full bg-[#0f172a] border border-[#334155] rounded-lg px-3 py-2 text-sm text-white"
            />
          </div>
          <div>
            <label className="block text-sm text-[#94a3b8] mb-1">Body template</label>
            <textarea
              required
              rows={6}
              value={bodyTemplate}
              onChange={(e) => setBodyTemplate(e.target.value)}
              className="w-full bg-[#0f172a] border border-[#334155] rounded-lg px-3 py-2 text-sm text-white resize-none font-mono"
            />
            <p className="text-xs text-[#475569] mt-1">
              Use {"{company_name}"}, {"{contact_name}"}, {"{industry}"} — AI will personalize per lead.
            </p>
          </div>
        </div>

        <div className="bg-[#1e293b] border border-[#334155] rounded-xl overflow-hidden">
          <div className="p-5 border-b border-[#334155] flex items-center justify-between">
            <h2 className="text-sm font-medium text-[#94a3b8] uppercase tracking-wide">
              Select leads ({selected.size} selected)
            </h2>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as LeadStatus | "")}
              className="bg-[#0f172a] border border-[#334155] rounded-lg px-2 py-1 text-xs text-[#cbd5e1]"
            >
              <option value="">All</option>
              <option value="enriched">Enriched</option>
              <option value="discovered">Discovered</option>
              <option value="qualified">Qualified</option>
            </select>
          </div>
          {loading ? (
            <div className="flex justify-center py-12">
              <div className="w-7 h-7 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : (
            <div className="max-h-80 overflow-y-auto divide-y divide-[#334155]">
              {leads.map((lead) => (
                <label
                  key={lead.id}
                  className="flex items-center gap-3 px-5 py-3 hover:bg-[#334155]/30 cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={lead.id ? selected.has(lead.id) : false}
                    onChange={() => lead.id && toggleLead(lead.id)}
                    className="rounded border-[#334155]"
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white truncate">{lead.company_info.name}</p>
                    <p className="text-xs text-[#64748b]">{lead.company_info.industry || "—"}</p>
                  </div>
                  <StatusBadge status={lead.status} />
                </label>
              ))}
            </div>
          )}
        </div>

        <button
          type="submit"
          disabled={submitting}
          className="cursor-pointer w-full bg-indigo-500 hover:bg-indigo-600 disabled:opacity-50 text-white font-medium py-3 rounded-lg transition"
        >
          {submitting ? "Generating emails with AI…" : "Create campaign & generate emails"}
        </button>
      </form>
    </div>
  );
}

export default function NewCampaignPage() {
  return (
    <Suspense fallback={<div className="text-[#64748b]">Loading…</div>}>
      <NewCampaignForm />
    </Suspense>
  );
}
