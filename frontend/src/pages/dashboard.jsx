
import {
  ArrowUpRight,
  UploadCloud,
  Box,
  Activity,
  FolderOpen,
  Plus,
  Clock3
} from "lucide-react";

const stats = [
  { label: "Total Projects", value: "0", icon: FolderOpen },
  { label: "3D Reconstructions", value: "0", icon: Box },
  { label: "Processing", value: "0", icon: Activity },
];

function Dashboard() {
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

        <button className="primary-button">
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
              <span className="stat-description">
                No records yet
              </span>
            </div>
          );
        })}
      </div>

      <div className="workspace-grid">

        <section className="upload-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">GET STARTED</p>
              <h2>Start a reconstruction</h2>
            </div>
            <UploadCloud size={23} />
          </div>

          <div className="upload-area">
            <div className="upload-icon">
              <UploadCloud size={29} />
            </div>

            <h3>Upload your medical scan</h3>

            <p>
              Begin your workflow by importing an image
              for AI-powered 3D generation.
            </p>

            <button className="primary-button">
              <Plus size={17} />
              Upload Scan
            </button>

            <span className="muted-note">
              Supported formats will be specified by the backend.
            </span>
          </div>
        </section>

        <section className="activity-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">WORKSPACE</p>
              <h2>Recent activity</h2>
            </div>
            <Clock3 size={21} />
          </div>

          <div className="empty-state">
            <div className="empty-icon">
              <FolderOpen size={27} />
            </div>

            <h3>No projects yet</h3>

            <p>
              Your reconstruction projects will
              appear here once you create them.
            </p>
          </div>
        </section>

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
