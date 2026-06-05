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
          <h1 className="text-2xl font-semibold text-white">Campaigns</h1>
          <p className="text-sm text-[#64748b] mt-0.5">{campaigns.length} email campaigns</p>
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

      <div className="bg-[#1e293b] border border-[#334155] rounded-xl overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-48">
            <div className="w-7 h-7 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : campaigns.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-[#64748b]">
            <p className="text-sm mb-3">No campaigns yet.</p>
            <Link href="/campaigns/new" className="text-indigo-400 hover:underline text-sm">
              Create your first campaign
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[#334155]">
                  <th className="text-left px-4 py-3 text-xs font-medium text-[#64748b] uppercase">Name</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-[#64748b] uppercase">Status</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-[#64748b] uppercase">Leads</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-[#64748b] uppercase">Sent</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-[#64748b] uppercase">Opened</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-[#64748b] uppercase">Created</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-[#334155]">
                {campaigns.map((c) => (
                  <tr
                    key={c.id}
                    className="hover:bg-[#334155]/40 transition cursor-pointer"
                    onClick={() => router.push(`/campaigns/${c.id}`)}
                  >
                    <td className="px-4 py-3 font-medium text-white">{c.name}</td>
                    <td className="px-4 py-3">
                      <CampaignStatusBadge status={c.status} />
                    </td>
                    <td className="px-4 py-3 text-[#94a3b8]">{c.total_leads}</td>
                    <td className="px-4 py-3 text-[#94a3b8]">{c.emails_sent}</td>
                    <td className="px-4 py-3 text-[#94a3b8]">{c.emails_opened}</td>
                    <td className="px-4 py-3 text-[#64748b] text-xs">
                      {new Date(c.created_at).toLocaleDateString()}
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
    </div>
  );
}
