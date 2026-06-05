import { CampaignStatus } from "@/lib/types";

const styles: Record<CampaignStatus, string> = {
  draft: "bg-slate-500/15 text-slate-400",
  scheduled: "bg-blue-500/15 text-blue-400",
  running: "bg-emerald-500/15 text-emerald-400",
  paused: "bg-yellow-500/15 text-yellow-400",
  completed: "bg-indigo-500/15 text-indigo-400",
  cancelled: "bg-red-500/15 text-red-400",
};

export default function CampaignStatusBadge({ status }: { status: CampaignStatus }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${styles[status] ?? "bg-gray-500/15 text-gray-400"}`}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}
