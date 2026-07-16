import { Fragment, useEffect, useState } from "react";
import { listDocuments, getDocument, deleteDocument } from "../api.js";
import StatusBadge from "../components/StatusBadge.jsx";

export default function DashboardPage() {
  const [documents, setDocuments] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState(null);
  const [expandedDoc, setExpandedDoc] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const result = await listDocuments(50, 0);
      setDocuments(result.items);
      setTotal(result.total);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    const interval = setInterval(load, 8000);
    return () => clearInterval(interval);
  }, []);

  const toggleExpand = async (id) => {
    if (expandedId === id) {
      setExpandedId(null);
      setExpandedDoc(null);
      return;
    }
    setExpandedId(id);
    setExpandedDoc(null);
    const detail = await getDocument(id);
    setExpandedDoc(detail);
  };

  const handleDelete = async (id, event) => {
    event.stopPropagation();
    if (!confirm("Delete this document and all its data?")) return;
    await deleteDocument(id);
    if (expandedId === id) {
      setExpandedId(null);
      setExpandedDoc(null);
    }
    load();
  };

  const stats = documents.reduce(
    (acc, d) => {
      acc.images += d.image_count;
      acc.chunks += d.chunk_count;
      acc[d.status] = (acc[d.status] || 0) + 1;
      return acc;
    },
    { images: 0, chunks: 0 }
  );

  return (
    <div className="mx-auto max-w-5xl px-8 py-10">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <span className="text-xs text-slate-500">{total} document{total === 1 ? "" : "s"}</span>
      </div>

      <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard label="Documents" value={total} />
        <StatCard label="Completed" value={stats.completed || 0} accent="emerald" />
        <StatCard label="Images" value={stats.images} />
        <StatCard label="Chunks" value={stats.chunks} />
      </div>

      <div className="mt-8 overflow-hidden rounded-xl border border-base-800">
        {loading && documents.length === 0 ? (
          <div className="p-8 text-center text-sm text-slate-500">Loading...</div>
        ) : documents.length === 0 ? (
          <div className="p-8 text-center text-sm text-slate-500">No documents uploaded yet.</div>
        ) : (
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-base-800 bg-base-900 text-xs uppercase tracking-wide text-slate-500">
                <th className="px-4 py-3 font-medium">Filename</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Pages</th>
                <th className="px-4 py-3 font-medium">Images</th>
                <th className="px-4 py-3 font-medium">Chunks</th>
                <th className="px-4 py-3 font-medium">Uploaded</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <Fragment key={doc.id}>
                  <tr
                    onClick={() => toggleExpand(doc.id)}
                    className="cursor-pointer border-b border-base-800 bg-base-950 transition-colors hover:bg-base-900"
                  >
                    <td className="px-4 py-3 font-medium text-slate-200">{doc.filename}</td>
                    <td className="px-4 py-3">
                      <StatusBadge status={doc.status} />
                    </td>
                    <td className="px-4 py-3 text-slate-400">{doc.page_count}</td>
                    <td className="px-4 py-3 text-slate-400">{doc.image_count}</td>
                    <td className="px-4 py-3 text-slate-400">{doc.chunk_count}</td>
                    <td className="px-4 py-3 text-slate-500">{new Date(doc.created_at).toLocaleString()}</td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={(e) => handleDelete(doc.id, e)}
                        className="rounded-md px-2 py-1 text-xs text-slate-500 hover:bg-rose-500/10 hover:text-rose-400"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                  {expandedId === doc.id && (
                    <tr className="border-b border-base-800 bg-base-900/40">
                      <td colSpan={7} className="px-4 py-4">
                        <ExpandedImages doc={expandedDoc} />
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function StatCard({ label, value, accent }) {
  return (
    <div className="rounded-xl border border-base-800 bg-base-900 p-4">
      <div className={`text-2xl font-bold ${accent === "emerald" ? "text-emerald-400" : "text-white"}`}>{value}</div>
      <div className="mt-0.5 text-xs text-slate-500">{label}</div>
    </div>
  );
}

function ExpandedImages({ doc }) {
  if (!doc) return <div className="text-xs text-slate-500">Loading images...</div>;
  if (doc.images.length === 0) {
    return <div className="text-xs text-slate-500">No images extracted from this document.</div>;
  }
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 md:grid-cols-6">
      {doc.images.map((img) => (
        <a
          key={img.id}
          href={img.cloudinary_url || undefined}
          target="_blank"
          rel="noreferrer"
          className="group overflow-hidden rounded-lg border border-base-800 bg-base-950"
        >
          {img.cloudinary_url ? (
            <img src={img.cloudinary_url} alt={img.description || "extracted"} className="h-20 w-full object-cover transition-transform group-hover:scale-105" />
          ) : (
            <div className="flex h-20 w-full items-center justify-center text-[10px] text-slate-600">no preview</div>
          )}
          <div className="truncate px-2 py-1 text-[10px] text-slate-500">
            p.{img.page_number} {img.image_type ? `· ${img.image_type}` : ""}
          </div>
        </a>
      ))}
    </div>
  );
}
