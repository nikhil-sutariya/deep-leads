"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { DashboardStats, TrendPoint } from "@/lib/types";

function StatCard({ label, value, sub, color }: { label: string; value: number | string; sub?: string; color: string }) {
  return (
    <div className="bg-[#1e293b] border border-[#334155] rounded-xl p-5">
      <p className="text-xs font-medium text-[#64748b] uppercase tracking-wide mb-2">{label}</p>
      <p className={`text-3xl font-bold ${color}`}>{value}</p>
      {sub && <p className="text-xs text-[#64748b] mt-1">{sub}</p>}
    </div>
  );
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [trends, setTrends] = useState<TrendPoint[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.get("/dashboard/stats"),
      api.get("/dashboard/trends"),
    ]).then(([s, t]) => {
      setStats(s.data.data);
      setTrends(t.data.data?.trends || []);
    }).catch(console.error).finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const maxTrend = Math.max(...trends.map((t) => t.count), 1);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-white">Dashboard</h1>
        <p className="text-sm text-[#64748b] mt-0.5">Overview of your lead generation activity</p>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard
          label="Total Leads"
          value={stats?.total_leads ?? 0}
          sub="All time"
          color="text-white"
        />
        <StatCard
          label="Enriched"
          value={stats?.total_enriched ?? 0}
          sub="With contact data"
          color="text-indigo-400"
        />
        <StatCard
          label="This Month"
          value={stats?.monthly_leads ?? 0}
          sub="New discoveries"
          color="text-emerald-400"
        />
      </div>

      {/* Trend chart */}
      {trends.length > 0 && (
        <div className="bg-[#1e293b] border border-[#334155] rounded-xl p-5">
          <h2 className="text-sm font-medium text-[#94a3b8] mb-4">Lead Discovery Trend (6 months)</h2>
          <div className="flex items-end gap-3 h-36">
            {trends.map((t) => (
              <div key={t.month} className="flex-1 flex flex-col items-center gap-1.5">
                <span className="text-xs text-[#64748b]">{t.count}</span>
                <div
                  className="w-full bg-indigo-500/80 rounded-t"
                  style={{ height: `${(t.count / maxTrend) * 100}%`, minHeight: t.count > 0 ? "4px" : "0" }}
                />
                <span className="text-xs text-[#64748b] whitespace-nowrap">{t.month_label}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Location breakdown */}
      {(stats?.location_breakdown?.length ?? 0) > 0 && (
        <div className="bg-[#1e293b] border border-[#334155] rounded-xl p-5">
          <h2 className="text-sm font-medium text-[#94a3b8] mb-3">Top Locations</h2>
          <div className="space-y-2">
            {stats!.location_breakdown.slice(0, 5).map((loc) => (
              <div key={loc.location} className="flex items-center justify-between text-sm">
                <span className="text-[#cbd5e1]">{loc.location || "Unknown"}</span>
                <span className="text-[#64748b]">{loc.count}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
