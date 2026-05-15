"use client";
import { useState, FormEvent } from "react";

interface Props {
  onClose: () => void;
  onDiscover: (query: string, maxResults: number) => void;
  discovering: boolean;
}

export default function DiscoverModal({ onClose, onDiscover, discovering }: Props) {
  const [query, setQuery] = useState("");
  const [maxResults, setMaxResults] = useState(20);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (query.trim().length < 20) return;
    onDiscover(query.trim(), maxResults);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-xl bg-[#1e293b] border border-[#334155] rounded-2xl shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-[#334155]">
          <div>
            <h2 className="text-base font-semibold text-white">Discover Leads</h2>
            <p className="text-xs text-[#64748b] mt-0.5">Describe the companies you're looking for</p>
          </div>
          <button onClick={onClose} disabled={discovering} className="text-[#475569] hover:text-white transition">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          <div>
            <label className="block text-sm font-medium text-[#94a3b8] mb-1.5">
              What companies are you looking for?
            </label>
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              disabled={discovering}
              rows={5}
              placeholder="e.g. SaaS startups in healthcare based in the US with 10-100 employees that have raised seed or Series A funding and are focused on AI-powered diagnostics..."
              className="w-full bg-[#0f172a] border border-[#334155] rounded-lg px-3.5 py-3 text-sm text-white placeholder-[#475569] focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition resize-none"
            />
            <p className="text-xs text-[#475569] mt-1">Minimum 20 characters. The more detail you give, the better the results.</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-[#94a3b8] mb-1.5">
              Max results
            </label>
            <select
              value={maxResults}
              onChange={(e) => setMaxResults(Number(e.target.value))}
              disabled={discovering}
              className="bg-[#0f172a] border border-[#334155] rounded-lg px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500 transition"
            >
              {[10, 20, 30, 50, 100].map((n) => (
                <option key={n} value={n}>{n} leads</option>
              ))}
            </select>
          </div>

          <div className="flex items-center justify-end gap-3 pt-1">
            <button
              type="button"
              onClick={onClose}
              disabled={discovering}
              className="px-4 py-2.5 text-sm text-[#94a3b8] hover:text-white border border-[#334155] rounded-lg transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={discovering || query.trim().length < 20}
              className="flex items-center gap-2 bg-indigo-500 hover:bg-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium px-5 py-2.5 rounded-lg transition"
            >
              {discovering ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Searching…
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-4.35-4.35M17 11A6 6 0 115 11a6 6 0 0112 0z" />
                  </svg>
                  Start Discovery
                </>
              )}
            </button>
          </div>
        </form>

        {/* Tip */}
        {discovering && (
          <div className="px-5 pb-5">
            <div className="bg-indigo-500/10 border border-indigo-500/20 rounded-lg p-3 text-xs text-indigo-300">
              Discovery is running in the background. This may take 30–60 seconds. You can close this modal and watch the leads appear.
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
