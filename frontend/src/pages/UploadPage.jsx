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
      <h1 className="text-2xl font-bold text-white">Upload a document</h1>
      <p className="mt-1 text-sm text-slate-400">
        Diagrams and screenshots inside your PDF get analysed and made searchable, not just the text.
      </p>

      <label
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={onDrop}
        className={`mt-8 flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-6 py-16 text-center transition-colors ${
          dragActive ? "border-accent-400 bg-accent-500/5" : "border-base-700 hover:border-base-600"
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={(e) => pickFile(e.target.files?.[0])}
        />
        <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-accent-500/10">
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-accent-400">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
        </div>
        {file ? (
          <>
            <div className="font-medium text-slate-200">{file.name}</div>
            <div className="mt-1 text-xs text-slate-500">{(file.size / 1024).toFixed(0)} KB — click to change</div>
          </>
        ) : (
          <>
            <div className="font-medium text-slate-300">Drop a PDF here, or click to browse</div>
            <div className="mt-1 text-xs text-slate-500">PDF files only</div>
          </>
        )}
      </label>

      <button
        onClick={handleUpload}
        disabled={!file || uploading}
        className="mt-6 w-full rounded-xl bg-gradient-to-r from-accent-500 to-accent-600 px-4 py-3 font-semibold text-white shadow-glow transition-opacity disabled:cursor-not-allowed disabled:opacity-40"
      >
        {uploading ? "Uploading..." : "Upload & Process"}
      </button>

      {error && (
        <div className="mt-4 rounded-lg border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-300">
          {error}
        </div>
      )}

      {doc && (
        <div className="animate-in mt-6 rounded-xl border border-base-800 bg-base-900 p-5">
          <div className="flex items-center justify-between">
            <div className="font-medium text-slate-200">{doc.filename}</div>
            <StatusBadge status={doc.status} />
          </div>
          {doc.status === "completed" && (
            <div className="mt-3 flex gap-4 text-xs text-slate-400">
              <span>{doc.page_count} pages</span>
              <span>{doc.image_count} images</span>
              <span>{doc.chunk_count} chunks</span>
            </div>
          )}
          {doc.status === "failed" && doc.error_message && (
            <div className="mt-3 text-xs text-rose-400">{doc.error_message}</div>
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
