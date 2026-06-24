"use client";
import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { api, WS_BASE } from "@/lib/api";
import { Lead, LeadStatus, ApiEnvelope, LeadListResponse, LeadManualCreate } from "@/lib/types";
import StatusBadge from "@/components/StatusBadge";
import DiscoverModal from "@/components/DiscoverModal";
import AddLeadModal from "@/components/AddLeadModal";

const PAGE_SIZE = 20;

export default function LeadsPage() {
  const router = useRouter();
  const [leads, setLeads] = useState<Lead[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<LeadStatus | "">("");
  const [ventureFilter, setVentureFilter] = useState("");
  const [ventures, setVentures] = useState<{ venture: string; count: number }[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [showDiscover, setShowDiscover] = useState(false);
  const [discovering, setDiscovering] = useState(false);
  const [discoverMsg, setDiscoverMsg] = useState("");
  const [showAddLead, setShowAddLead] = useState(false);
  const [addingLead, setAddingLead] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const selectAllRef = useRef<HTMLInputElement>(null);

  const fetchLeads = useCallback(async (p: number, status: LeadStatus | "", venture: string) => {
    setLoading(true);
    try {
      const skip = (p - 1) * PAGE_SIZE;
      const params: Record<string, unknown> = { skip, limit: PAGE_SIZE };
      if (status) params.status = status;
      if (venture) params.venture = venture;
      const res = await api.get<ApiEnvelope<LeadListResponse>>("/leads", { params });
      setLeads(res.data.data.leads);
      setTotal(res.data.data.total);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  const pageLeadIds = leads.map((l) => l.id).filter((id): id is string => !!id);
  const allPageSelected =
    pageLeadIds.length > 0 && pageLeadIds.every((id) => selectedIds.has(id));
  const somePageSelected =
    pageLeadIds.some((id) => selectedIds.has(id)) && !allPageSelected;

  function toggleSelectAllPage() {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (allPageSelected) {
        pageLeadIds.forEach((id) => next.delete(id));
      } else {
        pageLeadIds.forEach((id) => next.add(id));
      }
      return next;
    });
  }

  useEffect(() => {
    if (selectAllRef.current) {
      selectAllRef.current.indeterminate = somePageSelected;
    }
  }, [somePageSelected]);

  useEffect(() => {
    api.get<{ venture: string; count: number }[]>("/leads/ventures").then((res) => setVentures(res.data)).catch(() => {});
  }, []);

  useEffect(() => {
    fetchLeads(page, statusFilter, ventureFilter);
  }, [page, statusFilter, ventureFilter, fetchLeads]);

  // WebSocket for discovery notifications
  useEffect(() => {
    let ws: WebSocket;
    async function connectWs() {
      try {
        const res = await api.get<{ ws_token: string }>("/auth/ws-token");
        const token = res.data.ws_token;
        ws = new WebSocket(`${WS_BASE}/api/v1/auth/ws/notifications?token=${token}`);
        wsRef.current = ws;
        ws.onmessage = (evt) => {
          try {
            const data = JSON.parse(evt.data);
            if (data?.message) {
              setDiscoverMsg(data.message);
              // Refresh leads list when discovery completes
              if (data.message.toLowerCase().includes("discover") || data.message.toLowerCase().includes("found")) {
                fetchLeads(1, statusFilter, ventureFilter);
                setPage(1);
              }
            }
          } catch {
            // non-JSON heartbeat
          }
        };
      } catch {
        // WS optional — silently ignore
      }
    }
    connectWs();
    return () => {
      ws?.close();
    };
  }, [fetchLeads, statusFilter, ventureFilter]);

  async function handleDiscover(query: string, maxResults: number, venture?: string) {
    setDiscovering(true);
    setDiscoverMsg("Searching for leads…");
    try {
      const res = await api.post<ApiEnvelope<LeadListResponse>>("/leads/discover", {
        query,
        max_results: maxResults,
        venture: venture || undefined,
      });
      // Server message includes any "(N duplicates skipped)" detail.
      setDiscoverMsg(res.data.message || `Found ${res.data.data.leads.length} leads`);
      setShowDiscover(false);
      fetchLeads(1, statusFilter, ventureFilter);
      setPage(1);
      api.get<{ venture: string; count: number }[]>("/leads/ventures").then((r) => setVentures(r.data)).catch(() => {});
    } catch (e: unknown) {
      const msg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        "Discovery failed";
      setDiscoverMsg(msg);
    } finally {
      setDiscovering(false);
    }
  }

  async function handleAddLead(payload: LeadManualCreate) {
    setAddingLead(true);
    try {
      await api.post<ApiEnvelope<{ lead: Lead }>>("/leads", payload);
      setShowAddLead(false);
      setDiscoverMsg(`Added lead: ${payload.company_name}`);
      fetchLeads(1, statusFilter, ventureFilter);
      setPage(1);
      api.get<{ venture: string; count: number }[]>("/leads/ventures").then((r) => setVentures(r.data)).catch(() => {});
    } finally {
      setAddingLead(false);
    }
  }

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">Leads</h1>
          <p className="text-sm text-subtle mt-0.5">{total} total leads</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => { setDiscoverMsg(""); setShowAddLead(true); }}
            className="cursor-pointer flex items-center gap-2 border border-border text-foreground hover:bg-hover text-sm font-medium px-4 py-2.5 rounded-lg transition"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Add Lead
          </button>
          <button
            onClick={() => { setDiscoverMsg(""); setShowDiscover(true); }}
            className="cursor-pointer flex items-center gap-2 bg-indigo-500 hover:bg-indigo-600 text-white text-sm font-medium px-4 py-2.5 rounded-lg transition"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-4.35-4.35M17 11A6 6 0 115 11a6 6 0 0112 0z" />
            </svg>
            Discover Leads
          </button>
        </div>
      </div>

      {/* Notification bar */}
      {discoverMsg && (
        <div className="cursor-pointer bg-indigo-500/10 border border-indigo-500/30 rounded-lg px-4 py-3 text-sm text-indigo-300 flex items-center justify-between">
          <span>{discoverMsg}</span>
          <button onClick={() => setDiscoverMsg("")} className="text-subtle hover:text-foreground ml-4">✕</button>
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value as LeadStatus | ""); setPage(1); }}
          className="bg-card border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-indigo-500 transition"
        >
          <option value="">All statuses</option>
          {(["discovered","enriching","enriched","qualified","contacted","responded","converted","disqualified"] as LeadStatus[]).map((s) => (
            <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
          ))}
        </select>
        <select
          value={ventureFilter}
          onChange={(e) => { setVentureFilter(e.target.value); setPage(1); }}
          className="bg-card border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-indigo-500 transition"
        >
          <option value="">All ventures</option>
          {ventures.map((v) => (
            <option key={v.venture} value={v.venture}>{v.venture} ({v.count})</option>
          ))}
        </select>
        {selectedIds.size > 0 && (
          <a
            href={`/campaigns/new?leads=${Array.from(selectedIds).join(",")}`}
            className="text-sm bg-indigo-500 hover:bg-indigo-600 text-white px-4 py-2 rounded-lg transition"
          >
            Create campaign ({selectedIds.size})
          </a>
        )}
      </div>

      {/* Table */}
      <div className="bg-card border border-border rounded-xl overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-48">
            <div className="w-7 h-7 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : leads.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-subtle">
            <svg className="w-10 h-10 mb-3 opacity-40" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            <p className="text-sm">No leads found. Try discovering some!</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="px-4 py-3 w-10">
                    <input
                      ref={selectAllRef}
                      type="checkbox"
                      checked={allPageSelected}
                      onChange={toggleSelectAllPage}
                      disabled={pageLeadIds.length === 0}
                      aria-label="Select all leads on this page"
                      className="rounded border-border"
                    />
                  </th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-subtle uppercase tracking-wide">Company</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-subtle uppercase tracking-wide">Venture</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-subtle uppercase tracking-wide">Industry</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-subtle uppercase tracking-wide">Location</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-subtle uppercase tracking-wide">Employees</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-subtle uppercase tracking-wide">Status</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-subtle uppercase tracking-wide">Discovered</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {leads.map((lead) => (
                  <tr key={lead.id} className="hover:bg-hover/40 transition cursor-pointer" onClick={() => router.push(`/leads/${lead.id}`)}>
                    <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={lead.id ? selectedIds.has(lead.id) : false}
                        onChange={() => {
                          if (!lead.id) return;
                          setSelectedIds((prev) => {
                            const next = new Set(prev);
                            if (next.has(lead.id!)) next.delete(lead.id!);
                            else next.add(lead.id!);
                            return next;
                          });
                        }}
                        className="rounded border-border"
                      />
                    </td>
                    <td className="px-4 py-3">
                      <div>
                        <p className="font-medium text-foreground">{lead.company_info.name}</p>
                        {lead.company_info.website && (
                          <a
                            href={lead.company_info.website}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="text-xs text-indigo-400 hover:underline"
                          >
                            {lead.company_info.website.replace(/^https?:\/\//, "").replace(/\/$/, "")}
                          </a>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-muted text-xs">{lead.venture || "—"}</td>
                    <td className="px-4 py-3 text-muted">{lead.company_info.industry || "—"}</td>
                    <td className="px-4 py-3 text-muted">
                      {[lead.company_info.city, lead.company_info.country].filter(Boolean).join(", ") || lead.company_info.location || "—"}
                    </td>
                    <td className="px-4 py-3 text-muted">
                      {lead.company_info.employee_count ?? "—"}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={lead.status} />
                    </td>
                    <td className="px-4 py-3 text-subtle text-xs">
                      {new Date(lead.discovered_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3">
                      <svg className="w-4 h-4 text-faint" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between text-sm text-subtle">
          <span>Page {page} of {totalPages}</span>
          <div className="flex gap-2">
            <button
              disabled={page === 1}
              onClick={() => setPage(p => p - 1)}
              className="cursor-pointer px-3 py-1.5 rounded-lg border border-border disabled:opacity-40 hover:border-indigo-500 hover:text-foreground transition"
            >
              Previous
            </button>
            <button
              disabled={page === totalPages}
              onClick={() => setPage(p => p + 1)}
              className="cursor-pointer px-3 py-1.5 rounded-lg border border-border disabled:opacity-40 hover:border-indigo-500 hover:text-foreground transition"
            >
              Next
            </button>
          </div>
        </div>
      )}

      {/* Discover Modal */}
      {showDiscover && (
        <DiscoverModal
          onClose={() => setShowDiscover(false)}
          onDiscover={handleDiscover}
          discovering={discovering}
        />
      )}

      {/* Add Lead Modal */}
      {showAddLead && (
        <AddLeadModal
          onClose={() => setShowAddLead(false)}
          onCreate={handleAddLead}
          saving={addingLead}
        />
      )}
    </div>
  );
}
