import { useCallback, useEffect, useRef, useState } from "react";
import { uploadDocument, getDocument } from "../api.js";
import StatusBadge from "../components/StatusBadge.jsx";

export default function UploadPage() {
  const [dragActive, setDragActive] = useState(false);
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [doc, setDoc] = useState(null);
  const inputRef = useRef(null);
  const pollRef = useRef(null);

  useEffect(() => () => clearInterval(pollRef.current), []);

  const pickFile = (f) => {
    if (!f) return;
    setError(null);
    setDoc(null);
    setFile(f);
  };

  const onDrop = useCallback((event) => {
    event.preventDefault();
    setDragActive(false);
    pickFile(event.dataTransfer.files?.[0]);
  }, []);

  const startPolling = (id) => {
    clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const updated = await getDocument(id);
        setDoc(updated);
        if (updated.status === "completed" || updated.status === "failed") {
          clearInterval(pollRef.current);
        }
      } catch {
        clearInterval(pollRef.current);
      }
    }, 2000);
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      const result = await uploadDocument(file);
      setDoc(result);
      startPolling(result.id);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl px-8 py-12">
      <h1 className="text-2xl font-bold text-slate-900">Upload a document</h1>
      <p className="mt-1 text-sm text-slate-500">
        Diagrams and screenshots inside your PDF get analysed and made searchable, not just the text.
      </p>

      <label
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={onDrop}
        className={`mt-8 flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-16 text-center transition-colors ${
          dragActive ? "border-accent-500 bg-accent-50" : "border-slate-300 bg-slate-50 hover:border-slate-400"
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={(e) => pickFile(e.target.files?.[0])}
        />
        <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-accent-100">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-accent-600">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
        </div>
        {file ? (
          <>
            <div className="font-medium text-slate-800">{file.name}</div>
            <div className="mt-1 text-xs text-slate-500">{(file.size / 1024).toFixed(0)} KB — click to change</div>
          </>
        ) : (
          <>
            <div className="font-medium text-slate-700">Drop a PDF here, or click to browse</div>
            <div className="mt-1 text-xs text-slate-500">PDF files only</div>
          </>
        )}
      </label>

      <button
        onClick={handleUpload}
        disabled={!file || uploading}
        className="mt-6 w-full rounded-lg bg-accent-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-accent-700 disabled:cursor-not-allowed disabled:opacity-40"
      >
        {uploading ? "Uploading..." : "Upload & Process"}
      </button>

      {error && (
        <div className="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      )}

      {doc && (
        <div className="animate-in mt-6 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <div className="font-medium text-slate-800">{doc.filename}</div>
            <StatusBadge status={doc.status} />
          </div>
          {doc.status === "completed" && (
            <div className="mt-3 flex gap-4 text-xs text-slate-500">
              <span>{doc.page_count} pages</span>
              <span>{doc.image_count} images</span>
              <span>{doc.chunk_count} chunks</span>
            </div>
          )}
          {doc.status === "failed" && doc.error_message && (
            <div className="mt-3 text-xs text-rose-600">{doc.error_message}</div>
          )}
          {(doc.status === "queued" || doc.status === "processing") && (
            <div className="mt-3 text-xs text-slate-500">
              Processing in the background — this page updates automatically.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
