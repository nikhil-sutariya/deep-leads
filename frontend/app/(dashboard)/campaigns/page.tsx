"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Campaign } from "@/lib/types";
import CampaignStatusBadge from "@/components/CampaignStatusBadge";

export default function CampaignsPage() {
  const router = useRouter();
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get<Campaign[]>("/campaigns")
      .then((res) => setCampaigns(res.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">Campaigns</h1>
          <p className="text-sm text-subtle mt-0.5">{campaigns.length} email campaigns</p>
        </div>
        <Link
          href="/campaigns/new"
          className="flex items-center gap-2 bg-indigo-500 hover:bg-indigo-600 text-white text-sm font-medium px-4 py-2.5 rounded-lg transition"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          New Campaign
        </Link>
      </div>

      <div className="bg-card border border-border rounded-xl overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-48">
            <div className="w-7 h-7 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : campaigns.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-subtle">
            <p className="text-sm mb-3">No campaigns yet.</p>
            <Link href="/campaigns/new" className="text-indigo-400 hover:underline text-sm">
              Create your first campaign
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left px-4 py-3 text-xs font-medium text-subtle uppercase">Name</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-subtle uppercase">Status</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-subtle uppercase">Leads</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-subtle uppercase">Sent</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-subtle uppercase">Opened</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-subtle uppercase">Created</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {campaigns.map((c) => (
                  <tr
                    key={c.id}
                    className="hover:bg-hover/40 transition cursor-pointer"
                    onClick={() => router.push(`/campaigns/${c.id}`)}
                  >
                    <td className="px-4 py-3 font-medium text-foreground">{c.name}</td>
                    <td className="px-4 py-3">
                      <CampaignStatusBadge status={c.status} />
                    </td>
                    <td className="px-4 py-3 text-muted">{c.total_leads}</td>
                    <td className="px-4 py-3 text-muted">{c.emails_sent}</td>
                    <td className="px-4 py-3 text-muted">{c.emails_opened}</td>
                    <td className="px-4 py-3 text-subtle text-xs">
                      {new Date(c.created_at).toLocaleDateString()}
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
    </div>
  );
}
