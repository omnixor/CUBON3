
import {
  Box,
  Activity,
  FolderOpen,
  Plus
} from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getProjects } from "../services/api";

function Dashboard() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);

  useEffect(() => {
    let active = true;
    getProjects()
      .then((data) => active && setProjects(data.projects))
      .catch(() => active && setProjects([]));
    return () => { active = false; };
  }, []);

  const stats = [
    {
      label: "Total Projects",
      value: String(projects.length),
      description: projects.length ? "Saved in your workspace" : "No projects yet",
      icon: FolderOpen,
    },
    {
      label: "3D Reconstructions",
      value: String(projects.filter((item) => item.glb_file).length),
      description: "Models ready to explore",
      icon: Box,
    },
    {
      label: "Processing",
      value: String(projects.filter((item) => ["submitted", "processing"].includes(item.status)).length),
      description: "Tasks in progress",
      icon: Activity,
    },
  ];

  return (
    <div className="dashboard">

      <div className="welcome-section">
        <div>
          <p className="eyebrow">OVERVIEW</p>
          <h1>Welcome to your workspace.</h1>
          <p className="subtitle">
            Manage medical scans and explore 3D reconstructions.
          </p>
        </div>

        <button className="primary-button" onClick={() => navigate("/new-scan")}>
          <Plus size={18} />
          New Reconstruction
        </button>
      </div>

      <div className="stats-grid">
        {stats.map((stat) => {
          const Icon = stat.icon;

          return (
            <div className="stat-card" key={stat.label}>
              <div className="stat-top">
                <span>{stat.label}</span>
                <Icon size={20} />
              </div>

              <h2>{stat.value}</h2>
              <span className="stat-description">{stat.description}</span>
            </div>
          );
        })}
      </div>

      <section className="bottom-banner">
        <div>
          <p className="eyebrow">CUBON3 PLATFORM</p>
          <h2>From medical images to interactive 3D.</h2>
          <p>
            An experimental workspace for medical imaging
            and 3D reconstruction research.
          </p>
        </div>

        <Box size={55} />
      </section>

    </div>
  );
}

export default Dashboard;
