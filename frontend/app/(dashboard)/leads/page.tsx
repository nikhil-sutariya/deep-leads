"use client";
import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { api, WS_BASE } from "@/lib/api";
import { Lead, LeadStatus, ApiEnvelope, LeadListResponse } from "@/lib/types";
import StatusBadge from "@/components/StatusBadge";
import DiscoverModal from "@/components/DiscoverModal";

const PAGE_SIZE = 20;

export default function LeadsPage() {
  const router = useRouter();
  const [leads, setLeads] = useState<Lead[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<LeadStatus | "">("");
  const [loading, setLoading] = useState(true);
  const [showDiscover, setShowDiscover] = useState(false);
  const [discovering, setDiscovering] = useState(false);
  const [discoverMsg, setDiscoverMsg] = useState("");
  const wsRef = useRef<WebSocket | null>(null);

  const fetchLeads = useCallback(async (p: number, status: LeadStatus | "") => {
    setLoading(true);
    try {
      const skip = (p - 1) * PAGE_SIZE;
      const params: Record<string, unknown> = { skip, limit: PAGE_SIZE };
      if (status) params.status = status;
      const res = await api.get<ApiEnvelope<LeadListResponse>>("/leads", { params });
      setLeads(res.data.data.leads);
      setTotal(res.data.data.total);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLeads(page, statusFilter);
  }, [page, statusFilter, fetchLeads]);

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
                fetchLeads(1, statusFilter);
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
  }, [fetchLeads, statusFilter]);

  async function handleDiscover(query: string, maxResults: number) {
    setDiscovering(true);
    setDiscoverMsg("Searching for leads…");
    try {
      const res = await api.post<ApiEnvelope<LeadListResponse>>("/leads/discover", {
        query,
        max_results: maxResults,
      });
      const found = res.data.data.leads.length;
      setDiscoverMsg(`Found ${found} leads`);
      setShowDiscover(false);
      fetchLeads(1, statusFilter);
      setPage(1);
    } catch (e: unknown) {
      const msg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        "Discovery failed";
      setDiscoverMsg(msg);
    } finally {
      setDiscovering(false);
    }
  }

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white">Leads</h1>
          <p className="text-sm text-[#64748b] mt-0.5">{total} total leads</p>
        </div>
        <button
          onClick={() => { setDiscoverMsg(""); setShowDiscover(true); }}
          className="flex items-center gap-2 bg-indigo-500 hover:bg-indigo-600 text-white text-sm font-medium px-4 py-2.5 rounded-lg transition"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-4.35-4.35M17 11A6 6 0 115 11a6 6 0 0112 0z" />
          </svg>
          Discover Leads
        </button>
      </div>

      {/* Notification bar */}
      {discoverMsg && (
        <div className="bg-indigo-500/10 border border-indigo-500/30 rounded-lg px-4 py-3 text-sm text-indigo-300 flex items-center justify-between">
          <span>{discoverMsg}</span>
          <button onClick={() => setDiscoverMsg("")} className="text-[#64748b] hover:text-white ml-4">✕</button>
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-3">
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value as LeadStatus | ""); setPage(1); }}
          className="bg-[#1e293b] border border-[#334155] rounded-lg px-3 py-2 text-sm text-[#cbd5e1] focus:outline-none focus:border-indigo-500 transition"
        >
          <option value="">All statuses</option>
          {(["discovered","enriching","enriched","qualified","contacted","responded","converted","disqualified"] as LeadStatus[]).map((s) => (
            <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
          ))}
        </select>
      </div>

      {/* Table */}
      <div className="bg-[#1e293b] border border-[#334155] rounded-xl overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-48">
            <div className="w-7 h-7 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : leads.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-[#64748b]">
            <svg className="w-10 h-10 mb-3 opacity-40" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            <p className="text-sm">No leads found. Try discovering some!</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[#334155]">
                  <th className="text-left px-4 py-3 text-xs font-medium text-[#64748b] uppercase tracking-wide">Company</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-[#64748b] uppercase tracking-wide">Industry</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-[#64748b] uppercase tracking-wide">Location</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-[#64748b] uppercase tracking-wide">Employees</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-[#64748b] uppercase tracking-wide">Status</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-[#64748b] uppercase tracking-wide">Discovered</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-[#334155]">
                {leads.map((lead) => (
                  <tr key={lead.id} className="hover:bg-[#334155]/40 transition cursor-pointer" onClick={() => router.push(`/leads/${lead.id}`)}>
                    <td className="px-4 py-3">
                      <div>
                        <p className="font-medium text-white">{lead.company_info.name}</p>
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
                    <td className="px-4 py-3 text-[#94a3b8]">{lead.company_info.industry || "—"}</td>
                    <td className="px-4 py-3 text-[#94a3b8]">
                      {[lead.company_info.city, lead.company_info.country].filter(Boolean).join(", ") || lead.company_info.location || "—"}
                    </td>
                    <td className="px-4 py-3 text-[#94a3b8]">
                      {lead.company_info.employee_count ?? "—"}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={lead.status} />
                    </td>
                    <td className="px-4 py-3 text-[#64748b] text-xs">
                      {new Date(lead.discovered_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3">
                      <svg className="w-4 h-4 text-[#475569]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
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
        <div className="flex items-center justify-between text-sm text-[#64748b]">
          <span>Page {page} of {totalPages}</span>
          <div className="flex gap-2">
            <button
              disabled={page === 1}
              onClick={() => setPage(p => p - 1)}
              className="px-3 py-1.5 rounded-lg border border-[#334155] disabled:opacity-40 hover:border-indigo-500 hover:text-white transition"
            >
              Previous
            </button>
            <button
              disabled={page === totalPages}
              onClick={() => setPage(p => p + 1)}
              className="px-3 py-1.5 rounded-lg border border-[#334155] disabled:opacity-40 hover:border-indigo-500 hover:text-white transition"
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
    </div>
  );
}
