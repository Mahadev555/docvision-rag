const STYLES = {
  queued: "bg-slate-500/15 text-slate-300 ring-slate-500/30",
  processing: "bg-amber-500/15 text-amber-300 ring-amber-500/30",
  completed: "bg-emerald-500/15 text-emerald-300 ring-emerald-500/30",
  failed: "bg-rose-500/15 text-rose-300 ring-rose-500/30",
};

export default function StatusBadge({ status }) {
  const style = STYLES[status] || STYLES.queued;
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${style}`}>
      {status === "processing" && <span className="h-1.5 w-1.5 rounded-full bg-amber-400 dot-pulse" />}
      {status}
    </span>
  );
}
