
import { useEffect, useState } from "react";
import { NavLink } from "react-router-dom";

import {
  LayoutDashboard,
  ScanLine,
  Box,
  Ruler,
  FolderOpen,
  Settings,
  Bone
} from "lucide-react";

import { checkBackendHealth } from "../services/api";

const navigation = [
  { name: "Dashboard", icon: LayoutDashboard, path: "/" },
  { name: "New Scan", icon: ScanLine, path: "/new-scan" },
  { name: "3D Viewer", icon: Box, path: "/viewer" },
  { name: "Analysis", icon: Ruler, path: "/analysis" },
  { name: "Projects", icon: FolderOpen, path: "/projects" },
];

function Sidebar() {
  const [backendStatus, setBackendStatus] = useState("connecting");

  useEffect(() => {
    let isMounted = true;

    const checkConnection = async () => {
      try {
        await checkBackendHealth();

        if (isMounted) {
          setBackendStatus("connected");
        }
      } catch (error) {
        if (isMounted) {
          setBackendStatus("disconnected");
        }
      }
    };

    checkConnection();

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <aside className="sidebar">

      <div className="brand">
        <div className="brand-icon">
          <Bone size={23} />
        </div>

        <div>
          <h2>CUBON3</h2>
          <span>MEDICAL IMAGING</span>
        </div>
      </div>

      <div className="nav-section">
        <p className="nav-label">WORKSPACE</p>

        {navigation.map((item) => {
          const Icon = item.icon;

          return (
            <NavLink
              to={item.path}
              key={item.name}
              end={item.path === "/"}
              aria-label={item.name}
              title={item.name}
              className={({ isActive }) =>
                `nav-item ${isActive ? "active" : ""}`
              }
            >
              <Icon size={19} />
              <span>{item.name}</span>
            </NavLink>
          );
        })}
      </div>

      <div className="sidebar-bottom">

        <NavLink
          to="/settings"
          aria-label="Settings"
          title="Settings"
          className={({ isActive }) =>
            `nav-item ${isActive ? "active" : ""}`
          }
        >
          <Settings size={19} />
          <span>Settings</span>
        </NavLink>

        <div className="sidebar-footer">
          <span className={`status-dot ${backendStatus}`}></span>

          {backendStatus === "connecting" && "Connecting to backend..."}
          {backendStatus === "connected" && "Backend connected"}
          {backendStatus === "disconnected" && "Backend disconnected"}
        </div>

      </div>

    </aside>
  );
}

export default Sidebar;
