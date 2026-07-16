const STYLES = {
  queued: "bg-slate-100 text-slate-600 ring-slate-200",
  processing: "bg-amber-50 text-amber-700 ring-amber-200",
  completed: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  failed: "bg-rose-50 text-rose-700 ring-rose-200",
};

export default function StatusBadge({ status }) {
  const style = STYLES[status] || STYLES.queued;
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${style}`}>
      {status === "processing" && <span className="h-1.5 w-1.5 rounded-full bg-amber-500 dot-pulse" />}
      {status}
    </span>
  );
}
