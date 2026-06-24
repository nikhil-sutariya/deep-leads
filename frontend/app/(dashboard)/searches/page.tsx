"use client";
import { FormEvent, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { SavedSearch, SavedSearchPayload } from "@/lib/types";

const inputClass =
  "w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder-faint focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition";
const labelClass = "block text-xs font-medium text-muted mb-1";

const CADENCE_LABEL: Record<string, string> = { off: "Manual", daily: "Daily", weekly: "Weekly" };

function SearchModal({
  initial,
  onClose,
  onSave,
  saving,
}: {
  initial?: SavedSearch | null;
  onClose: () => void;
  onSave: (payload: SavedSearchPayload) => Promise<void>;
  saving: boolean;
}) {
  const [name, setName] = useState(initial?.name ?? "");
  const [query, setQuery] = useState(initial?.query ?? "");
  const [maxResults, setMaxResults] = useState(initial?.max_results ?? 25);
  const [venture, setVenture] = useState(initial?.venture ?? "");
  const [cadence, setCadence] = useState<SavedSearch["cadence"]>(initial?.cadence ?? "off");
  const [error, setError] = useState("");

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!name.trim() || query.trim().length < 20) {
      setError("Name is required and the query must be at least 20 characters.");
      return;
    }
    setError("");
    await onSave({
      name: name.trim(),
      query: query.trim(),
      max_results: maxResults,
      venture: venture.trim() || undefined,
      cadence,
    });
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-xl bg-card border border-border rounded-2xl shadow-2xl">
        <div className="flex items-center justify-between p-5 border-b border-border">
          <h2 className="text-base font-semibold text-foreground">{initial ? "Edit saved search" : "New saved search"}</h2>
          <button onClick={onClose} disabled={saving} className="cursor-pointer text-faint hover:text-foreground transition">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <form onSubmit={submit} className="p-5 space-y-4">
          {error && <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2 text-sm text-red-400">{error}</div>}
          <div>
            <label className={labelClass}>Name</label>
            <input value={name} onChange={(e) => setName(e.target.value)} className={inputClass} placeholder="US garage-door companies with visualizers" />
          </div>
          <div>
            <label className={labelClass}>Discovery query</label>
            <textarea value={query} onChange={(e) => setQuery(e.target.value)} rows={5} className={`${inputClass} resize-none`} placeholder="Describe the companies to find… (min 20 chars)" />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className={labelClass}>Max results</label>
              <select value={maxResults} onChange={(e) => setMaxResults(Number(e.target.value))} className={inputClass}>
                {[10, 25, 50, 100].map((n) => <option key={n} value={n}>{n}</option>)}
              </select>
            </div>
            <div>
              <label className={labelClass}>Cadence</label>
              <select value={cadence} onChange={(e) => setCadence(e.target.value as SavedSearch["cadence"])} className={inputClass}>
                <option value="off">Manual only</option>
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
              </select>
            </div>
            <div>
              <label className={labelClass}>Venture tag</label>
              <input value={venture} onChange={(e) => setVenture(e.target.value)} className={inputClass} placeholder="optional" />
            </div>
          </div>
          <p className="text-xs text-faint">Scheduled runs use AI discovery and only add companies you don&apos;t already have.</p>
          <div className="flex justify-end gap-2 pt-1">
            <button type="button" onClick={onClose} disabled={saving} className="cursor-pointer px-4 py-2 text-sm text-muted hover:text-foreground border border-border rounded-lg">Cancel</button>
            <button type="submit" disabled={saving} className="cursor-pointer bg-indigo-500 hover:bg-indigo-600 disabled:opacity-50 text-white text-sm px-5 py-2 rounded-lg">{saving ? "Saving…" : "Save"}</button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function SearchesPage() {
  const [searches, setSearches] = useState<SavedSearch[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState<SavedSearch | null>(null);
  const [saving, setSaving] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [msg, setMsg] = useState("");

  function load() {
    setLoading(true);
    api.get<SavedSearch[]>("/saved-searches").then((r) => setSearches(r.data)).catch(console.error).finally(() => setLoading(false));
  }
  useEffect(load, []);

  async function handleSave(payload: SavedSearchPayload) {
    setSaving(true);
    try {
      if (editing) await api.patch(`/saved-searches/${editing.id}`, payload);
      else await api.post("/saved-searches", payload);
      setShowModal(false);
      setEditing(null);
      load();
    } finally {
      setSaving(false);
    }
  }

  async function runNow(s: SavedSearch) {
    setBusyId(s.id);
    setMsg("");
    try {
      const r = await api.post<{ message: string }>(`/saved-searches/${s.id}/run`);
      setMsg(`${s.name}: ${r.data.message}`);
      load();
    } catch {
      setMsg(`${s.name}: run failed`);
    } finally {
      setBusyId(null);
    }
  }

  async function toggleEnabled(s: SavedSearch) {
    await api.patch(`/saved-searches/${s.id}`, { enabled: !s.enabled });
    load();
  }

  async function remove(s: SavedSearch) {
    if (!window.confirm(`Delete saved search "${s.name}"?`)) return;
    await api.delete(`/saved-searches/${s.id}`);
    load();
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">Saved Searches</h1>
          <p className="text-sm text-subtle mt-0.5">Re-run discovery on a schedule — only new companies are added</p>
        </div>
        <button onClick={() => { setEditing(null); setShowModal(true); }} className="cursor-pointer flex items-center gap-2 bg-indigo-500 hover:bg-indigo-600 text-white text-sm font-medium px-4 py-2.5 rounded-lg transition">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
          New saved search
        </button>
      </div>

      {msg && (
        <div className="bg-indigo-500/10 border border-indigo-500/30 rounded-lg px-4 py-3 text-sm text-indigo-300 flex items-center justify-between">
          <span>{msg}</span>
          <button onClick={() => setMsg("")} className="text-subtle hover:text-foreground ml-4">✕</button>
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-16"><div className="w-7 h-7 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" /></div>
      ) : searches.length === 0 ? (
        <div className="bg-card border border-border rounded-xl p-10 text-center text-subtle text-sm">No saved searches yet. Create one to automate discovery.</div>
      ) : (
        <div className="space-y-3">
          {searches.map((s) => (
            <div key={s.id} className="bg-card border border-border rounded-xl p-5">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="text-sm font-semibold text-foreground">{s.name}</h3>
                    <span className={`text-xs px-2 py-0.5 rounded ${s.cadence === "off" ? "bg-hover text-muted" : "bg-indigo-500/15 text-indigo-400"}`}>{CADENCE_LABEL[s.cadence]}</span>
                    {!s.enabled && <span className="text-xs px-2 py-0.5 rounded bg-hover text-faint">Paused</span>}
                    {s.venture && <span className="text-xs text-faint">#{s.venture}</span>}
                  </div>
                  <p className="text-xs text-subtle mt-1.5 line-clamp-2">{s.query}</p>
                  <p className="text-xs text-faint mt-2">
                    {s.last_run_at ? `Last run ${new Date(s.last_run_at).toLocaleString()} · +${s.last_run_new_count} new` : "Never run"}
                    {` · ${s.total_found} found total`}
                  </p>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <button onClick={() => runNow(s)} disabled={busyId === s.id} className="cursor-pointer bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white text-xs px-3 py-1.5 rounded-lg">{busyId === s.id ? "Running…" : "Run now"}</button>
                  <button onClick={() => toggleEnabled(s)} className="cursor-pointer border border-border text-muted hover:text-foreground text-xs px-3 py-1.5 rounded-lg">{s.enabled ? "Pause" : "Enable"}</button>
                  <button onClick={() => { setEditing(s); setShowModal(true); }} className="cursor-pointer border border-border text-muted hover:text-foreground text-xs px-3 py-1.5 rounded-lg">Edit</button>
                  <button onClick={() => remove(s)} className="cursor-pointer border border-red-500/40 text-red-400 hover:bg-red-500/10 text-xs px-3 py-1.5 rounded-lg">Delete</button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {showModal && (
        <SearchModal
          initial={editing}
          onClose={() => { setShowModal(false); setEditing(null); }}
          onSave={handleSave}
          saving={saving}
        />
      )}
    </div>
  );
}
