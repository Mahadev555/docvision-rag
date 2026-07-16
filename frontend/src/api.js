const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const API = `${API_BASE}/api/v1`;

async function handleJson(response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = data?.error?.message || data?.detail || `Request failed (${response.status})`;
    throw new Error(message);
  }
  return data;
}

export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${API}/documents/upload`, { method: "POST", body: formData });
  return handleJson(response);
}

export async function listDocuments(limit = 50, offset = 0) {
  const response = await fetch(`${API}/documents?limit=${limit}&offset=${offset}`);
  return handleJson(response);
}

export async function getDocument(id) {
  const response = await fetch(`${API}/documents/${id}`);
  return handleJson(response);
}

export async function deleteDocument(id) {
  const response = await fetch(`${API}/documents/${id}`, { method: "DELETE" });
  if (!response.ok && response.status !== 204) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data?.error?.message || `Delete failed (${response.status})`);
  }
}

export async function getHealth() {
  const response = await fetch(`${API}/health`);
  return handleJson(response);
}

/**
 * Stream a chat answer via SSE. The backend emits frames shaped like:
 *   event: metadata\ndata: {...}\n\n
 *   event: token\ndata: {...}\n\n
 *   event: done\ndata: {...}\n\n
 * Each frame's `data:` line is JSON carrying its own `type`, which we use
 * directly rather than re-parsing the `event:` line.
 */
export async function streamChat(payload, { onMetadata, onToken, onDone, onError }) {
  try {
    const response = await fetch(`${API}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...payload, stream: true }),
    });

    if (!response.ok || !response.body) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data?.error?.message || `Chat request failed (${response.status})`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let boundary = buffer.indexOf("\n\n");
      while (boundary !== -1) {
        const frame = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);

        const dataLine = frame.split("\n").find((line) => line.startsWith("data:"));
        if (dataLine) {
          const event = JSON.parse(dataLine.slice(5).trim());
          if (event.type === "metadata") onMetadata?.(event);
          else if (event.type === "token") onToken?.(event.content);
          else if (event.type === "done") onDone?.();
        }
        boundary = buffer.indexOf("\n\n");
      }
    }
  } catch (err) {
    onError?.(err);
  }
}
