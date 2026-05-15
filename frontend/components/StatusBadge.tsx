import { LeadStatus } from "@/lib/types";

const styles: Record<LeadStatus, string> = {
  discovered:    "bg-blue-500/15 text-blue-400",
  enriching:     "bg-yellow-500/15 text-yellow-400",
  enriched:      "bg-indigo-500/15 text-indigo-400",
  qualified:     "bg-violet-500/15 text-violet-400",
  contacted:     "bg-orange-500/15 text-orange-400",
  responded:     "bg-cyan-500/15 text-cyan-400",
  converted:     "bg-emerald-500/15 text-emerald-400",
  disqualified:  "bg-red-500/15 text-red-400",
};

export default function StatusBadge({ status }: { status: LeadStatus }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${styles[status] ?? "bg-gray-500/15 text-gray-400"}`}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}
