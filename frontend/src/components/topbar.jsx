
import { Search, Bell, CircleHelp } from "lucide-react";

function Topbar() {
  return (
    <header className="topbar">

      <div className="breadcrumb">
        Workspace <span>/</span> Dashboard
      </div>

      <div className="topbar-actions">
        <div className="search-box">
          <Search size={17} />
          <input placeholder="Search workspace..." />
          <kbd>Ctrl K</kbd>
        </div>

        <button className="icon-button">
          <CircleHelp size={19} />
        </button>

        <button className="icon-button">
          <Bell size={19} />
        </button>

        <div className="avatar">S</div>
      </div>

    </header>
  );
}

export default Topbar;
