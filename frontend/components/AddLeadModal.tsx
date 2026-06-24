"use client";
import { FormEvent, useState } from "react";
import { ContactInfo, LeadManualCreate } from "@/lib/types";

interface Props {
  onClose: () => void;
  onCreate: (payload: LeadManualCreate) => Promise<void>;
  saving: boolean;
}

const inputClass =
  "w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder-faint focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition";
const labelClass = "block text-xs font-medium text-muted mb-1";

function emptyContact(): ContactInfo {
  return { name: "", title: "", email: "", phone: "", linkedin_url: "" };
}

const FUNDING_STAGES = [
  "",
  "Pre-Seed",
  "Seed",
  "Series A",
  "Series B",
  "Series C+",
  "Bootstrapped",
  "Public",
  "Unknown",
];

export default function AddLeadModal({ onClose, onCreate, saving }: Props) {
  const [form, setForm] = useState<LeadManualCreate>({ company_name: "" });
  const [decisionMakers, setDecisionMakers] = useState<ContactInfo[]>([emptyContact()]);
  const [techStack, setTechStack] = useState("");
  const [error, setError] = useState("");

  function set<K extends keyof LeadManualCreate>(key: K, value: LeadManualCreate[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function updateDM(index: number, field: keyof ContactInfo, value: string) {
    setDecisionMakers((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], [field]: value };
      return next;
    });
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!form.company_name.trim()) {
      setError("Company name is required");
      return;
    }
    setError("");

    const cleanedDMs = decisionMakers.filter(
      (dm) => dm.name || dm.title || dm.email || dm.phone || dm.linkedin_url
    );

    const payload: LeadManualCreate = {
      ...form,
      company_name: form.company_name.trim(),
      employee_count: form.employee_count ? Number(form.employee_count) : undefined,
      founded_year: form.founded_year ? Number(form.founded_year) : undefined,
      funding_amount_millions: form.funding_amount_millions
        ? Number(form.funding_amount_millions)
        : undefined,
      tech_stack: techStack
        ? techStack.split(",").map((t) => t.trim()).filter(Boolean)
        : undefined,
      decision_makers: cleanedDMs.length ? cleanedDMs : undefined,
    };

    try {
      await onCreate(payload);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        "Failed to create lead";
      setError(typeof msg === "string" ? msg : "Failed to create lead");
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-2xl bg-card border border-border rounded-2xl shadow-2xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-border flex-shrink-0">
          <div>
            <h2 className="text-base font-semibold text-foreground">Add Lead</h2>
            <p className="text-xs text-subtle mt-0.5">Only the company name is required</p>
          </div>
          <button onClick={onClose} disabled={saving} className="cursor-pointer text-faint hover:text-foreground transition">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <form onSubmit={handleSubmit} className="p-5 space-y-5 overflow-y-auto">
          {error && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2 text-sm text-red-400">
              {error}
            </div>
          )}

          {/* Company */}
          <div>
            <h3 className="text-xs font-semibold text-muted uppercase tracking-wide mb-2">Company</h3>
            <div className="grid grid-cols-2 gap-3">
              <div className="col-span-2">
                <label className={labelClass}>Company name *</label>
                <input
                  required
                  value={form.company_name}
                  onChange={(e) => set("company_name", e.target.value)}
                  className={inputClass}
                  placeholder="Acme Garage Doors"
                />
              </div>
              <div>
                <label className={labelClass}>Website</label>
                <input value={form.website ?? ""} onChange={(e) => set("website", e.target.value)} className={inputClass} placeholder="acme.com" />
              </div>
              <div>
                <label className={labelClass}>Industry</label>
                <input value={form.industry ?? ""} onChange={(e) => set("industry", e.target.value)} className={inputClass} placeholder="Home services" />
              </div>
              <div>
                <label className={labelClass}>Employees</label>
                <input type="number" min={0} value={form.employee_count ?? ""} onChange={(e) => set("employee_count", e.target.value ? Number(e.target.value) : undefined)} className={inputClass} />
              </div>
              <div>
                <label className={labelClass}>Founded year</label>
                <input type="number" value={form.founded_year ?? ""} onChange={(e) => set("founded_year", e.target.value ? Number(e.target.value) : undefined)} className={inputClass} placeholder="2015" />
              </div>
              <div className="col-span-2">
                <label className={labelClass}>Description</label>
                <textarea rows={2} value={form.description ?? ""} onChange={(e) => set("description", e.target.value)} className={`${inputClass} resize-none`} />
              </div>
            </div>
          </div>

          {/* Contact */}
          <div>
            <h3 className="text-xs font-semibold text-muted uppercase tracking-wide mb-2">Contact</h3>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className={labelClass}>Email</label>
                <input value={form.email ?? ""} onChange={(e) => set("email", e.target.value)} className={inputClass} placeholder="info@acme.com" />
              </div>
              <div>
                <label className={labelClass}>Phone</label>
                <input value={form.phone ?? ""} onChange={(e) => set("phone", e.target.value)} className={inputClass} />
              </div>
              <div className="col-span-2">
                <label className={labelClass}>Address</label>
                <input value={form.address ?? ""} onChange={(e) => set("address", e.target.value)} className={inputClass} />
              </div>
              <div>
                <label className={labelClass}>City</label>
                <input value={form.city ?? ""} onChange={(e) => set("city", e.target.value)} className={inputClass} />
              </div>
              <div>
                <label className={labelClass}>Country</label>
                <input value={form.country ?? ""} onChange={(e) => set("country", e.target.value)} className={inputClass} placeholder="USA" />
              </div>
            </div>
          </div>

          {/* Funding & capabilities */}
          <div>
            <h3 className="text-xs font-semibold text-muted uppercase tracking-wide mb-2">Funding & capabilities</h3>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className={labelClass}>Funding stage</label>
                <select value={form.funding_stage ?? ""} onChange={(e) => set("funding_stage", e.target.value || undefined)} className={inputClass}>
                  {FUNDING_STAGES.map((s) => (
                    <option key={s} value={s}>{s || "—"}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className={labelClass}>Funding amount ($M)</label>
                <input type="number" step="0.1" min={0} value={form.funding_amount_millions ?? ""} onChange={(e) => set("funding_amount_millions", e.target.value ? Number(e.target.value) : undefined)} className={inputClass} />
              </div>
              <div className="col-span-2">
                <label className={labelClass}>Tech stack / specialisations (comma-separated)</label>
                <input value={techStack} onChange={(e) => setTechStack(e.target.value)} className={inputClass} placeholder="React, Shopify, AR visualizer" />
              </div>
            </div>
          </div>

          {/* Decision makers */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs font-semibold text-muted uppercase tracking-wide">Decision makers</h3>
              <button type="button" onClick={() => setDecisionMakers((p) => [...p, emptyContact()])} className="cursor-pointer text-xs text-indigo-400 hover:underline">
                + Add
              </button>
            </div>
            <div className="space-y-3">
              {decisionMakers.map((dm, i) => (
                <div key={i} className="border border-border rounded-lg p-3 space-y-2">
                  <div className="grid grid-cols-2 gap-2">
                    <input value={dm.name ?? ""} onChange={(e) => updateDM(i, "name", e.target.value)} className={inputClass} placeholder="Name" />
                    <input value={dm.title ?? ""} onChange={(e) => updateDM(i, "title", e.target.value)} className={inputClass} placeholder="Title" />
                    <input value={dm.email ?? ""} onChange={(e) => updateDM(i, "email", e.target.value)} className={inputClass} placeholder="Email" />
                    <input value={dm.phone ?? ""} onChange={(e) => updateDM(i, "phone", e.target.value)} className={inputClass} placeholder="Phone" />
                    <input value={dm.linkedin_url ?? ""} onChange={(e) => updateDM(i, "linkedin_url", e.target.value)} className={`${inputClass} col-span-2`} placeholder="LinkedIn URL" />
                  </div>
                  {decisionMakers.length > 1 && (
                    <button type="button" onClick={() => setDecisionMakers((p) => p.filter((_, idx) => idx !== i))} className="cursor-pointer text-xs text-red-400 hover:underline">
                      Remove
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Venture & notes */}
          <div>
            <h3 className="text-xs font-semibold text-muted uppercase tracking-wide mb-2">Organisation</h3>
            <div className="grid grid-cols-1 gap-3">
              <div>
                <label className={labelClass}>Venture tag</label>
                <input value={form.venture ?? ""} onChange={(e) => set("venture", e.target.value)} className={inputClass} placeholder="garage-door-api" />
              </div>
              <div>
                <label className={labelClass}>Notes</label>
                <textarea rows={2} value={form.notes ?? ""} onChange={(e) => set("notes", e.target.value)} className={`${inputClass} resize-none`} />
              </div>
            </div>
          </div>

          <div className="flex items-center justify-end gap-3 pt-1">
            <button type="button" onClick={onClose} disabled={saving} className="cursor-pointer px-4 py-2.5 text-sm text-muted hover:text-foreground border border-border rounded-lg transition">
              Cancel
            </button>
            <button type="submit" disabled={saving || !form.company_name.trim()} className="cursor-pointer bg-indigo-500 hover:bg-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium px-5 py-2.5 rounded-lg transition">
              {saving ? "Saving…" : "Add Lead"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
