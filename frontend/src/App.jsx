import { Routes, Route, Navigate } from "react-router-dom";
import Sidebar from "./components/Sidebar.jsx";
import UploadPage from "./pages/UploadPage.jsx";
import ChatPage from "./pages/ChatPage.jsx";
import DashboardPage from "./pages/DashboardPage.jsx";

export default function App() {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-base-950">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <Routes>
          <Route path="/" element={<Navigate to="/chat" replace />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
        </Routes>
      </main>
    </div>
  );
}
