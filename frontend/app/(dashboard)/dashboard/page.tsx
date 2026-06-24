"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Analytics, DashboardStats, TrendPoint } from "@/lib/types";

function StatCard({ label, value, sub, color }: { label: string; value: number | string; sub?: string; color: string }) {
  return (
    <div className="bg-card border border-border rounded-xl p-5">
      <p className="text-xs font-medium text-subtle uppercase tracking-wide mb-2">{label}</p>
      <p className={`text-3xl font-bold ${color}`}>{value}</p>
      {sub && <p className="text-xs text-subtle mt-1">{sub}</p>}
    </div>
  );
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [trends, setTrends] = useState<TrendPoint[]>([]);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.get("/dashboard/stats"),
      api.get("/dashboard/trends"),
      api.get("/dashboard/analytics"),
    ]).then(([s, t, a]) => {
      setStats(s.data.data);
      setTrends(t.data.data?.trends || []);
      setAnalytics(a.data.data);
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
  const ep = analytics?.email_performance;
  const maxFunnel = Math.max(...(analytics?.funnel.map((f) => f.count) ?? [0]), 1);
  const maxHour = Math.max(...(analytics?.best_send_hours.map((h) => h.open_rate) ?? [0]), 1);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Dashboard</h1>
        <p className="text-sm text-subtle mt-0.5">Overview of your lead generation activity</p>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard
          label="Total Leads"
          value={stats?.total_leads ?? 0}
          sub="All time"
          color="text-foreground"
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
        <div className="bg-card border border-border rounded-xl p-5">
          <h2 className="text-sm font-medium text-muted mb-4">Lead Discovery Trend (6 months)</h2>
          <div className="flex items-end gap-3 h-36">
            {trends.map((t) => (
              <div key={t.month} className="flex-1 flex flex-col items-center gap-1.5">
                <span className="text-xs text-subtle">{t.count}</span>
                <div
                  className="w-full bg-indigo-500/80 rounded-t"
                  style={{ height: `${(t.count / maxTrend) * 100}%`, minHeight: t.count > 0 ? "4px" : "0" }}
                />
                <span className="text-xs text-subtle whitespace-nowrap">{t.month_label}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Lead funnel */}
      {analytics && analytics.funnel.some((f) => f.count > 0) && (
        <div className="bg-card border border-border rounded-xl p-5">
          <h2 className="text-sm font-medium text-muted mb-4">Lead Funnel</h2>
          <div className="space-y-2.5">
            {analytics.funnel.map((f) => (
              <div key={f.key} className="flex items-center gap-3">
                <span className="w-24 text-xs text-subtle flex-shrink-0">{f.stage}</span>
                <div className="flex-1 bg-background rounded h-6 overflow-hidden">
                  <div className="h-full bg-indigo-500/80 rounded flex items-center justify-end px-2" style={{ width: `${Math.max((f.count / maxFunnel) * 100, f.count > 0 ? 6 : 0)}%` }}>
                    {f.count > 0 && <span className="text-xs text-white">{f.count}</span>}
                  </div>
                </div>
                {f.count === 0 && <span className="text-xs text-faint w-6">0</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Email performance */}
      {ep && ep.sent > 0 && (
        <div className="bg-card border border-border rounded-xl p-5">
          <h2 className="text-sm font-medium text-muted mb-4">Email Performance</h2>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
            {[
              { label: "Sent", value: ep.sent, color: "text-foreground" },
              { label: "Open rate", value: `${ep.open_rate}%`, color: "text-indigo-400" },
              { label: "Click rate", value: `${ep.click_rate}%`, color: "text-foreground" },
              { label: "Reply rate", value: `${ep.reply_rate}%`, color: "text-emerald-400" },
              { label: "Bounce rate", value: `${ep.bounce_rate}%`, color: "text-amber-400" },
            ].map((m) => (
              <div key={m.label}>
                <p className="text-xs text-subtle">{m.label}</p>
                <p className={`text-2xl font-bold mt-0.5 ${m.color}`}>{m.value}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Top subjects + best send time */}
      {analytics && (analytics.top_subjects.length > 0 || analytics.best_send_hours.length > 0) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {analytics.top_subjects.length > 0 && (
            <div className="bg-card border border-border rounded-xl p-5">
              <h2 className="text-sm font-medium text-muted mb-3">Top Subjects by Open Rate</h2>
              <div className="space-y-2.5">
                {analytics.top_subjects.map((s) => (
                  <div key={s.subject} className="text-sm">
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-foreground truncate">{s.subject}</span>
                      <span className="text-indigo-400 flex-shrink-0">{s.open_rate}%</span>
                    </div>
                    <p className="text-xs text-faint">{s.opens}/{s.sends} opened</p>
                  </div>
                ))}
              </div>
            </div>
          )}
          {analytics.best_send_hours.length > 0 && (
            <div className="bg-card border border-border rounded-xl p-5">
              <h2 className="text-sm font-medium text-muted mb-4">Open Rate by Send Hour (UTC)</h2>
              <div className="flex items-end gap-1 h-32">
                {analytics.best_send_hours.map((h) => (
                  <div key={h.hour} className="flex-1 flex flex-col items-center gap-1" title={`${h.hour}:00 — ${h.open_rate}% (${h.sends} sent)`}>
                    <div className="w-full bg-emerald-500/70 rounded-t" style={{ height: `${(h.open_rate / maxHour) * 100}%`, minHeight: h.open_rate > 0 ? "3px" : "0" }} />
                    <span className="text-[10px] text-faint">{h.hour}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Reply rate breakdowns */}
      {analytics && (analytics.by_country.length > 0 || analytics.by_industry.length > 0) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {([["Reply Rate by Country", analytics.by_country], ["Reply Rate by Industry", analytics.by_industry]] as const).map(
            ([title, rows]) => rows.length > 0 && (
              <div key={title} className="bg-card border border-border rounded-xl p-5">
                <h2 className="text-sm font-medium text-muted mb-3">{title}</h2>
                <div className="space-y-2">
                  {rows.map((r) => (
                    <div key={r.label} className="flex items-center justify-between text-sm">
                      <span className="text-foreground truncate">{r.label}</span>
                      <span className="text-subtle flex-shrink-0">{r.reply_rate}% <span className="text-faint">({r.replied}/{r.sent})</span></span>
                    </div>
                  ))}
                </div>
              </div>
            )
          )}
        </div>
      )}

      {/* Location breakdown */}
      {(stats?.location_breakdown?.length ?? 0) > 0 && (
        <div className="bg-card border border-border rounded-xl p-5">
          <h2 className="text-sm font-medium text-muted mb-3">Top Locations</h2>
          <div className="space-y-2">
            {stats!.location_breakdown.slice(0, 5).map((loc) => (
              <div key={loc.location} className="flex items-center justify-between text-sm">
                <span className="text-foreground">{loc.location || "Unknown"}</span>
                <span className="text-subtle">{loc.count}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
