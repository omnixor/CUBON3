
import { NavLink, useLocation } from "react-router-dom";

import {
  LayoutDashboard,
  ScanLine,
  FolderOpen,
  FileText,
  Apple,
  BookOpen,
  Settings,
  Bone
} from "lucide-react";

const navigation = [
  { name: "Dashboard", icon: LayoutDashboard, path: "/" },
  { name: "Scan Workspace", icon: ScanLine, path: "/new-scan" },
  { name: "3D Model Summary", icon: FileText, path: "/analysis" },
  { name: "Nutrition", icon: Apple, path: "/nutrition" },
  { name: "Bone Academy", icon: BookOpen, path: "/academy" },
  { name: "Projects", icon: FolderOpen, path: "/projects" },
];

function Sidebar() {
  const { pathname } = useLocation();

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
              className={() =>
                `nav-item ${
                  pathname === item.path ||
                  (item.path === "/new-scan" && pathname === "/viewer")
                    ? "active"
                    : ""
                }`
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

      </div>

    </aside>
  );
}

export default Sidebar;
