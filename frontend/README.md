# DocVision Frontend

A simple React + Vite + Tailwind UI for the DocVision backend. Three pages: **Upload**, **Chat** (streaming), and **Dashboard**.

## Stack

- React + Vite
- Tailwind CSS + `@tailwindcss/typography`
- `react-markdown` for rendering chat answers
- Plain `fetch`, no state library — just binds to the existing FastAPI backend

## Run it

Backend must be running separately on `http://localhost:8000` (see the root README).

```bash
npm install
npm run dev
```

Opens at `http://localhost:5173`.

## Config

`.env`:
```
VITE_API_BASE_URL=http://localhost:8000
```

## Pages

- **Upload** (`/upload`) — drag-and-drop PDF upload, polls status until `completed`/`failed`.
- **Chat** (`/chat`) — streams answers via SSE, shows cited sources and ranked result images.
- **Dashboard** (`/dashboard`) — lists all documents with stats, click a row to preview its extracted images, delete documents.

## Build

```bash
npm run build   # outputs to dist/
npm run preview # serve the production build locally
```
