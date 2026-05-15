"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Lead, ApiEnvelope } from "@/lib/types";
import StatusBadge from "@/components/StatusBadge";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-[#1e293b] border border-[#334155] rounded-xl p-5">
      <h2 className="text-sm font-medium text-[#94a3b8] uppercase tracking-wide mb-4">{title}</h2>
      {children}
    </div>
  );
}

function Field({ label, value }: { label: string; value?: string | number | null }) {
  if (!value && value !== 0) return null;
  return (
    <div>
      <p className="text-xs text-[#64748b] mb-0.5">{label}</p>
      <p className="text-sm text-[#cbd5e1]">{value}</p>
    </div>
  );
}

export default function LeadDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [lead, setLead] = useState<Lead | null>(null);
  const [loading, setLoading] = useState(true);
  const [enriching, setEnriching] = useState(false);
  const [enrichMsg, setEnrichMsg] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api.get<ApiEnvelope<{ lead: Lead }>>(`/leads/${params.id}`)
      .then((res) => setLead(res.data.data.lead))
      .catch(() => setError("Lead not found"))
      .finally(() => setLoading(false));
  }, [params.id]);

  async function handleEnrich() {
    if (!lead) return;
    setEnriching(true);
    setEnrichMsg("");
    try {
      const res = await api.post<ApiEnvelope<{ lead: Lead }>>(`/leads/${params.id}/enrich`);
      setLead(res.data.data.lead);
      setEnrichMsg("Lead enriched successfully");
    } catch {
      setEnrichMsg("Enrichment failed. Please try again.");
    } finally {
      setEnriching(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (error || !lead) {
    return (
      <div className="text-center py-16 text-[#64748b]">
        <p className="mb-4">{error || "Lead not found"}</p>
        <button onClick={() => router.push("/leads")} className="text-indigo-400 hover:underline text-sm">
          ← Back to leads
        </button>
      </div>
    );
  }

  const ci = lead.company_info;
  const ed = lead.enrichment_data;
  const canEnrich = lead.status === "discovered" || lead.status === "enriched" || lead.status === "enriching";

  return (
    <div className="space-y-5 max-w-4xl">
      {/* Back */}
      <button
        onClick={() => router.push("/leads")}
        className="flex items-center gap-1.5 text-sm text-[#64748b] hover:text-white transition"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        Back to leads
      </button>

      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-white">{ci.name}</h1>
          {ci.website && (
            <a href={ci.website} target="_blank" rel="noopener noreferrer" className="text-sm text-indigo-400 hover:underline">
              {ci.website.replace(/^https?:\/\//, "").replace(/\/$/, "")}
            </a>
          )}
        </div>
        <div className="flex items-center gap-3 flex-shrink-0">
          <StatusBadge status={lead.status} />
          <button
            onClick={handleEnrich}
            disabled={enriching}
            className="flex items-center gap-2 bg-indigo-500 hover:bg-indigo-600 disabled:opacity-60 text-white text-sm font-medium px-4 py-2 rounded-lg transition"
          >
            {enriching ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Enriching…
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Enrich Lead
              </>
            )}
          </button>
        </div>
      </div>

      {enrichMsg && (
        <div className={`rounded-lg px-4 py-3 text-sm flex items-center justify-between ${
          enrichMsg.includes("success") ? "bg-emerald-500/10 border border-emerald-500/30 text-emerald-400" : "bg-red-500/10 border border-red-500/30 text-red-400"
        }`}>
          <span>{enrichMsg}</span>
          <button onClick={() => setEnrichMsg("")} className="ml-4 text-[#64748b] hover:text-white">✕</button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Company Info */}
        <Section title="Company Information">
          <div className="space-y-3">
            <Field label="Description" value={ci.description} />
            <Field label="Industry" value={ci.industry} />
            <Field label="Employees" value={ci.employee_count} />
            <Field label="Founded" value={ci.founded_year} />
            <Field label="Funding Stage" value={ci.funding_stage} />
            {ci.funding_amount_millions && (
              <Field label="Funding Amount" value={`$${ci.funding_amount_millions}M`} />
            )}
          </div>
        </Section>

        {/* Contact */}
        <Section title="Contact Details">
          <div className="space-y-3">
            <Field label="Email" value={ci.email} />
            <Field label="Phone" value={ci.phone} />
            <Field label="Address" value={ci.address} />
            <Field label="City" value={ci.city} />
            <Field label="Country" value={ci.country} />
            <Field label="Location" value={ci.location} />
          </div>
        </Section>

        {/* Tech Stack */}
        {(ci.tech_stack?.length ?? 0) > 0 && (
          <Section title="Tech Stack">
            <div className="flex flex-wrap gap-2">
              {ci.tech_stack!.map((t) => (
                <span key={t} className="bg-[#334155] text-[#94a3b8] text-xs px-2.5 py-1 rounded-full">{t}</span>
              ))}
            </div>
          </Section>
        )}

        {/* Social Media */}
        {ed?.social_media && Object.keys(ed.social_media).length > 0 && (
          <Section title="Social Media">
            <div className="space-y-2">
              {Object.entries(ed.social_media).map(([platform, url]) =>
                url ? (
                  <div key={platform} className="flex items-center gap-2">
                    <span className="text-xs text-[#64748b] w-20 capitalize">{platform}</span>
                    <a href={url} target="_blank" rel="noopener noreferrer" className="text-sm text-indigo-400 hover:underline truncate">
                      {url.replace(/^https?:\/\//, "")}
                    </a>
                  </div>
                ) : null
              )}
            </div>
          </Section>
        )}
      </div>

      {/* Decision Makers */}
      {(ed?.decision_makers?.length ?? 0) > 0 && (
        <Section title="Decision Makers">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {ed!.decision_makers!.map((dm, i) => (
              <div key={i} className="bg-[#0f172a] border border-[#334155] rounded-lg p-3 space-y-1.5">
                <p className="text-sm font-medium text-white">{dm.name || "—"}</p>
                {dm.title && <p className="text-xs text-indigo-400">{dm.title}</p>}
                {dm.email && <p className="text-xs text-[#94a3b8]">{dm.email}</p>}
                {dm.phone && <p className="text-xs text-[#94a3b8]">{dm.phone}</p>}
                {dm.linkedin_url && (
                  <a href={dm.linkedin_url} target="_blank" rel="noopener noreferrer" className="text-xs text-indigo-400 hover:underline block">
                    LinkedIn ↗
                  </a>
                )}
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* No enrichment yet */}
      {!ed && !enriching && (
        <div className="bg-[#1e293b] border border-dashed border-[#334155] rounded-xl p-8 text-center">
          <svg className="w-10 h-10 mx-auto mb-3 text-[#334155]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="text-sm text-[#64748b]">No enrichment data yet.</p>
          <p className="text-xs text-[#475569] mt-1">Click <strong className="text-[#64748b]">Enrich Lead</strong> to find contact details and decision makers.</p>
        </div>
      )}

      {/* Metadata */}
      <div className="text-xs text-[#475569] space-y-0.5">
        <p>Discovered: {new Date(lead.discovered_at).toLocaleString()}</p>
        {lead.enriched_at && <p>Enriched: {new Date(lead.enriched_at).toLocaleString()}</p>}
        {lead.notes && <p>Notes: {lead.notes}</p>}
      </div>
    </div>
  );
}
