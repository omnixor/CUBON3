
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  useLocation,
  Link,
} from "react-router-dom";

import Sidebar from "./components/sidebar";
import Topbar from "./components/topbar";
import Dashboard from "./pages/dashboard";
import { BoneAcademy, Nutrition } from "./pages/learningPages";

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
          <ScanWorkflow />

          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/new-scan" element={<NewScan />} />
            <Route path="/viewer" element={<Viewer />} />
            <Route path="/analysis" element={<Analysis />} />
            <Route path="/nutrition" element={<Nutrition />} />
            <Route path="/academy" element={<BoneAcademy />} />
            <Route path="/projects" element={<Projects />} />
            <Route path="/settings" element={<SettingsPage />} />

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

function ScanWorkflow() {
  const { pathname, search } = useLocation();
  const steps = [
    { label: "Import scan", path: "/new-scan" },
    { label: "Explore 3D", path: "/viewer" },
    { label: "Model summary", path: "/analysis" },
  ];
  const activeStep = steps.findIndex((step) => step.path === pathname);

  if (activeStep < 0) return null;

  const taskId = new URLSearchParams(search).get("task");
  const taskQuery = taskId ? `?task=${encodeURIComponent(taskId)}` : "";

  return (
    <nav className="scan-workflow" aria-label="Scan workflow">
      {steps.map((step, index) => {
        const path = `${step.path}${taskQuery}`;
        const state = index === activeStep ? "active" : "";

        return (
          <Link
            key={step.path}
            className={`scan-workflow-step ${state}`}
            to={path}
            aria-current={index === activeStep ? "step" : undefined}
          >
            <span className="scan-workflow-number">{index + 1}</span>
            <span>{step.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}

export default App;
