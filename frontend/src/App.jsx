
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import Sidebar from "./components/sidebar";
import Topbar from "./components/topbar";
import Dashboard from "./pages/dashboard";

import {
  NewScan,
  Viewer,
  Analysis,
  Projects,
  SettingsPage
} from "./pages/workspacePages";

function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <Sidebar />

        <main className="main-content">
          <Topbar />

          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/new-scan" element={<NewScan />} />
            <Route path="/viewer" element={<Viewer />} />
            <Route path="/analysis" element={<Analysis />} />
            <Route path="/projects" element={<Projects />} />
            <Route path="/settings" element={<SettingsPage />} />

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
