
function PageLayout({ title, description, icon }) {
  return (
    <section style={{
      padding: "32px",
      color: "#e8edf7"
    }}>
      <div style={{
        display: "flex",
        alignItems: "center",
        gap: "14px",
        marginBottom: "24px"
      }}>
        <div style={{
          width: "46px",
          height: "46px",
          borderRadius: "13px",
          background: "#172b49",
          display: "grid",
          placeItems: "center",
          fontSize: "22px"
        }}>
          {icon}
        </div>

        <div>
          <h1 style={{ margin: 0, fontSize: "26px" }}>
            {title}
          </h1>
          <p style={{
            margin: "6px 0 0",
            color: "#8996aa"
          }}>
            {description}
          </p>
        </div>
      </div>

      <div style={{
        padding: "32px",
        border: "1px solid #26354b",
        borderRadius: "14px",
        background: "#101a2a"
      }}>
        <h3 style={{ marginTop: 0 }}>Coming next</h3>
        <p style={{ color: "#8996aa", lineHeight: 1.7 }}>
          This workspace is ready for implementation.
          Its functionality will be added in the next development stage.
        </p>
      </div>
    </section>
  );
}

export function NewScan() {
  return (
    <PageLayout
      title="New Scan"
      description="Upload medical images for 3D generation."
      icon="📤"
    />
  );
}

export function Viewer() {
  return (
    <PageLayout
      title="3D Viewer"
      description="View and interact with generated 3D models."
      icon="🦴"
    />
  );
}

export function Analysis() {
  return (
    <PageLayout
      title="Analysis"
      description="Review available scan and generation information."
      icon="📊"
    />
  );
}

export function Projects() {
  return (
    <PageLayout
      title="Projects"
      description="Manage your generated 3D reconstruction projects."
      icon="📁"
    />
  );
}

export function SettingsPage() {
  return (
    <PageLayout
      title="Settings"
      description="Manage your CUBON3 workspace."
      icon="⚙️"
    />
  );
}
