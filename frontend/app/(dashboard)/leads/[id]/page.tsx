"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import Link from "next/link";
import { Lead, ApiEnvelope, LeadCampaignHistory, ContactInfo, LeadContactUpdate } from "@/lib/types";
import StatusBadge from "@/components/StatusBadge";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-card border border-border rounded-xl p-5">
      <h2 className="text-sm font-medium text-muted uppercase tracking-wide mb-4">{title}</h2>
      {children}
    </div>
  );
}

function Field({ label, value }: { label: string; value?: string | number | null }) {
  if (!value && value !== 0) return null;
  return (
    <div>
      <p className="text-xs text-subtle mb-0.5">{label}</p>
      <p className="text-sm text-foreground">{value}</p>
    </div>
  );
}

function emptyContact(): ContactInfo {
  return { name: "", title: "", email: "", phone: "", linkedin_url: "" };
}

function leadToEditForm(lead: Lead): LeadContactUpdate {
  const ci = lead.company_info;
  return {
    email: ci.email ?? "",
    phone: ci.phone ?? "",
    address: ci.address ?? "",
    city: ci.city ?? "",
    country: ci.country ?? "",
    notes: lead.notes ?? "",
    decision_makers:
      lead.enrichment_data?.decision_makers?.length
        ? lead.enrichment_data.decision_makers.map((dm) => ({
            name: dm.name ?? "",
            title: dm.title ?? "",
            email: dm.email ?? "",
            phone: dm.phone ?? "",
            linkedin_url: dm.linkedin_url ?? "",
          }))
        : [emptyContact()],
  };
}

const inputClass =
  "w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder-faint focus:outline-none focus:border-indigo-500";

export default function LeadDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [lead, setLead] = useState<Lead | null>(null);
  const [loading, setLoading] = useState(true);
  const [enriching, setEnriching] = useState(false);
  const [enrichMsg, setEnrichMsg] = useState("");
  const [error, setError] = useState("");
  const [campaignHistory, setCampaignHistory] = useState<LeadCampaignHistory[]>([]);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editForm, setEditForm] = useState<LeadContactUpdate>({});

  useEffect(() => {
    api.get<ApiEnvelope<{ lead: Lead }>>(`/leads/${params.id}`)
      .then((res) => setLead(res.data.data.lead))
      .catch(() => setError("Lead not found"))
      .finally(() => setLoading(false));

    api
      .get<{ success: boolean; data: LeadCampaignHistory[] }>(`/leads/${params.id}/campaigns`)
      .then((res) => setCampaignHistory(res.data.data))
      .catch(() => {});
  }, [params.id]);

  function startEditing() {
    if (!lead) return;
    setEditForm(leadToEditForm(lead));
    setEditing(true);
    setEnrichMsg("");
  }

  function cancelEditing() {
    setEditing(false);
    setEditForm({});
  }

  function updateDecisionMaker(index: number, field: keyof ContactInfo, value: string) {
    setEditForm((prev) => {
      const dms = [...(prev.decision_makers ?? [])];
      dms[index] = { ...dms[index], [field]: value };
      return { ...prev, decision_makers: dms };
    });
  }

  function addDecisionMaker() {
    setEditForm((prev) => ({
      ...prev,
      decision_makers: [...(prev.decision_makers ?? []), emptyContact()],
    }));
  }

  function removeDecisionMaker(index: number) {
    setEditForm((prev) => {
      const dms = [...(prev.decision_makers ?? [])];
      dms.splice(index, 1);
      return { ...prev, decision_makers: dms.length ? dms : [emptyContact()] };
    });
  }

  async function handleSaveContacts() {
    setSaving(true);
    setEnrichMsg("");
    try {
      const res = await api.patch<ApiEnvelope<{ lead: Lead }>>(`/leads/${params.id}`, editForm);
      setLead(res.data.data.lead);
      setEditing(false);
      setEnrichMsg("Contact details saved");
    } catch {
      setEnrichMsg("Failed to save contact details");
    } finally {
      setSaving(false);
    }
  }

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
      <div className="text-center py-16 text-subtle">
        <p className="mb-4">{error || "Lead not found"}</p>
        <button onClick={() => router.push("/leads")} className="cursor-pointer text-indigo-400 hover:underline text-sm">
          ← Back to leads
        </button>
      </div>
    );
  }

  const ci = lead.company_info;
  const ed = lead.enrichment_data;

  return (
    <div className="space-y-5 max-w-4xl">
      <button
        onClick={() => router.push("/leads")}
        className="cursor-pointer flex items-center gap-1.5 text-sm text-subtle hover:text-foreground transition"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        Back to leads
      </button>

      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">{ci.name}</h1>
          {ci.website && (
            <a href={ci.website} target="_blank" rel="noopener noreferrer" className="text-sm text-indigo-400 hover:underline">
              {ci.website.replace(/^https?:\/\//, "").replace(/\/$/, "")}
            </a>
          )}
        </div>
        <div className="flex items-center gap-3 flex-shrink-0 flex-wrap justify-end">
          <StatusBadge status={lead.status} />
          {lead.id && !editing && (
            <Link
              href={`/campaigns/new?leads=${lead.id}`}
              className="text-sm border border-border text-muted hover:text-foreground px-3 py-2 rounded-lg transition"
            >
              Add to campaign
            </Link>
          )}
          {!editing && (
            <button
              onClick={startEditing}
              className="cursor-pointer flex items-center gap-2 border border-border text-muted hover:text-foreground text-sm font-medium px-4 py-2 rounded-lg transition"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
              Edit contacts
            </button>
          )}
          {!editing && (
            <button
              onClick={handleEnrich}
              disabled={enriching}
              className="cursor-pointer flex items-center gap-2 bg-indigo-500 hover:bg-indigo-600 disabled:opacity-60 text-white text-sm font-medium px-4 py-2 rounded-lg transition"
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
          )}
        </div>
      </div>

      {enrichMsg && (
        <div
          className={`rounded-lg px-4 py-3 text-sm flex items-center justify-between ${
            enrichMsg.includes("success") || enrichMsg.includes("saved")
              ? "bg-emerald-500/10 border border-emerald-500/30 text-emerald-400"
              : "bg-red-500/10 border border-red-500/30 text-red-400"
          }`}
        >
          <span>{enrichMsg}</span>
          <button onClick={() => setEnrichMsg("")} className="cursor-pointer ml-4 text-subtle hover:text-foreground">
            ✕
          </button>
        </div>
      )}

      {editing ? (
        <div className="space-y-4">
          <Section title="Company contact">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-subtle mb-1">Company email</label>
                <input
                  type="email"
                  value={editForm.email ?? ""}
                  onChange={(e) => setEditForm((p) => ({ ...p, email: e.target.value }))}
                  className={inputClass}
                  placeholder="info@company.com"
                />
              </div>
              <div>
                <label className="block text-xs text-subtle mb-1">Phone</label>
                <input
                  value={editForm.phone ?? ""}
                  onChange={(e) => setEditForm((p) => ({ ...p, phone: e.target.value }))}
                  className={inputClass}
                  placeholder="+1 555 000 0000"
                />
              </div>
              <div className="sm:col-span-2">
                <label className="block text-xs text-subtle mb-1">Address</label>
                <input
                  value={editForm.address ?? ""}
                  onChange={(e) => setEditForm((p) => ({ ...p, address: e.target.value }))}
                  className={inputClass}
                />
              </div>
              <div>
                <label className="block text-xs text-subtle mb-1">City</label>
                <input
                  value={editForm.city ?? ""}
                  onChange={(e) => setEditForm((p) => ({ ...p, city: e.target.value }))}
                  className={inputClass}
                />
              </div>
              <div>
                <label className="block text-xs text-subtle mb-1">Country</label>
                <input
                  value={editForm.country ?? ""}
                  onChange={(e) => setEditForm((p) => ({ ...p, country: e.target.value }))}
                  className={inputClass}
                />
              </div>
              <div className="sm:col-span-2">
                <label className="block text-xs text-subtle mb-1">Notes</label>
                <textarea
                  rows={2}
                  value={editForm.notes ?? ""}
                  onChange={(e) => setEditForm((p) => ({ ...p, notes: e.target.value }))}
                  className={`${inputClass} resize-none`}
                />
              </div>
            </div>
          </Section>

          <Section title="Decision makers">
            <p className="text-xs text-subtle mb-4">
              Add or fix contacts the AI missed. The first contact with an email is used for campaigns.
            </p>
            <div className="space-y-4">
              {(editForm.decision_makers ?? []).map((dm, i) => (
                <div key={i} className="bg-background border border-border rounded-lg p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-muted">Contact {i + 1}</span>
                    {(editForm.decision_makers?.length ?? 0) > 1 && (
                      <button
                        type="button"
                        onClick={() => removeDecisionMaker(i)}
                        className="cursor-pointer text-xs text-red-400 hover:text-red-300"
                      >
                        Remove
                      </button>
                    )}
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs text-subtle mb-1">Name</label>
                      <input
                        value={dm.name ?? ""}
                        onChange={(e) => updateDecisionMaker(i, "name", e.target.value)}
                        className={inputClass}
                        placeholder="Jane Smith"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-subtle mb-1">Title</label>
                      <input
                        value={dm.title ?? ""}
                        onChange={(e) => updateDecisionMaker(i, "title", e.target.value)}
                        className={inputClass}
                        placeholder="VP Product"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-subtle mb-1">Email</label>
                      <input
                        type="email"
                        value={dm.email ?? ""}
                        onChange={(e) => updateDecisionMaker(i, "email", e.target.value)}
                        className={inputClass}
                        placeholder="jane@company.com"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-subtle mb-1">Phone</label>
                      <input
                        value={dm.phone ?? ""}
                        onChange={(e) => updateDecisionMaker(i, "phone", e.target.value)}
                        className={inputClass}
                      />
                    </div>
                    <div className="sm:col-span-2">
                      <label className="block text-xs text-subtle mb-1">LinkedIn URL</label>
                      <input
                        value={dm.linkedin_url ?? ""}
                        onChange={(e) => updateDecisionMaker(i, "linkedin_url", e.target.value)}
                        className={inputClass}
                        placeholder="https://linkedin.com/in/..."
                      />
                    </div>
                  </div>
                </div>
              ))}
              <button
                type="button"
                onClick={addDecisionMaker}
                className="cursor-pointer text-sm text-indigo-400 hover:text-indigo-300"
              >
                + Add another contact
              </button>
            </div>
          </Section>

          <div className="flex gap-3 justify-end">
            <button
              type="button"
              onClick={cancelEditing}
              disabled={saving}
              className="cursor-pointer px-4 py-2.5 text-sm text-muted border border-border rounded-lg hover:text-foreground transition"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSaveContacts}
              disabled={saving}
              className="cursor-pointer bg-indigo-500 hover:bg-indigo-600 disabled:opacity-50 text-white text-sm font-medium px-5 py-2.5 rounded-lg transition"
            >
              {saving ? "Saving…" : "Save contacts"}
            </button>
          </div>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
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

            {(ci.tech_stack?.length ?? 0) > 0 && (
              <Section title="Tech Stack">
                <div className="flex flex-wrap gap-2">
                  {ci.tech_stack!.map((t) => (
                    <span key={t} className="bg-hover text-muted text-xs px-2.5 py-1 rounded-full">
                      {t}
                    </span>
                  ))}
                </div>
              </Section>
            )}

            {ed?.social_media && Object.keys(ed.social_media).length > 0 && (
              <Section title="Social Media">
                <div className="space-y-2">
                  {Object.entries(ed.social_media).map(([platform, url]) =>
                    url ? (
                      <div key={platform} className="flex items-center gap-2">
                        <span className="text-xs text-subtle w-20 capitalize">{platform}</span>
                        <a
                          href={url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sm text-indigo-400 hover:underline truncate"
                        >
                          {url.replace(/^https?:\/\//, "")}
                        </a>
                      </div>
                    ) : null
                  )}
                </div>
              </Section>
            )}
          </div>

          {(ed?.decision_makers?.length ?? 0) > 0 ? (
            <Section title="Decision Makers">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {ed!.decision_makers!.map((dm, i) => (
                  <div key={i} className="bg-background border border-border rounded-lg p-3 space-y-1.5">
                    <p className="text-sm font-medium text-foreground">{dm.name || "—"}</p>
                    {dm.title && <p className="text-xs text-indigo-400">{dm.title}</p>}
                    {dm.email ? (
                      <p className="text-xs text-muted">{dm.email}</p>
                    ) : (
                      <p className="text-xs text-amber-400/80">No email — use Edit contacts</p>
                    )}
                    {dm.phone && <p className="text-xs text-muted">{dm.phone}</p>}
                    {dm.linkedin_url && (
                      <a
                        href={dm.linkedin_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-indigo-400 hover:underline block"
                      >
                        LinkedIn ↗
                      </a>
                    )}
                  </div>
                ))}
              </div>
            </Section>
          ) : (
            !enriching && (
              <div className="bg-card border border-dashed border-border rounded-xl p-8 text-center">
                <p className="text-sm text-subtle">No decision makers yet.</p>
                <p className="text-xs text-faint mt-1">
                  Run <strong className="text-subtle">Enrich Lead</strong> or use{" "}
                  <strong className="text-subtle">Edit contacts</strong> to add them manually.
                </p>
              </div>
            )
          )}
        </>
      )}

      {!editing && campaignHistory.length > 0 && (
        <Section title="Campaign history">
          <div className="space-y-2">
            {campaignHistory.map((c) => (
              <Link
                key={c.email_id}
                href={`/campaigns/${c.campaign_id}`}
                className="flex items-center justify-between bg-background border border-border rounded-lg px-3 py-2 hover:border-indigo-500/50 transition"
              >
                <div>
                  <p className="text-sm text-foreground">{c.campaign_name}</p>
                  <p className="text-xs text-subtle truncate">{c.subject || "—"}</p>
                </div>
                <span className="text-xs text-faint">
                  {c.sent_at ? new Date(c.sent_at).toLocaleDateString() : "Draft"}
                  {c.follow_up_number > 0 ? ` · FU${c.follow_up_number}` : ""}
                </span>
              </Link>
            ))}
          </div>
        </Section>
      )}

      {!editing && (
        <div className="text-xs text-faint space-y-0.5">
          {lead.venture && <p>Venture: {lead.venture}</p>}
          <p>Discovered: {new Date(lead.discovered_at).toLocaleString()}</p>
          {lead.enriched_at && <p>Enriched: {new Date(lead.enriched_at).toLocaleString()}</p>}
          {lead.notes && <p>Notes: {lead.notes}</p>}
        </div>
      )}
    </div>
  );
}
