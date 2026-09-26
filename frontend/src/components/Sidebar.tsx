import { Link } from "react-router-dom";
import {
  LayoutDashboard,
  Bell,
  FolderSearch,
} from "lucide-react";

import "../styles/sidebar.css";

type SidebarProps = {
  activePage: "dashboard" | "alerts" | "investigations";
};

export default function Sidebar({ activePage }: SidebarProps) {
  return (
    <aside className="app-sidebar">

      {/* Workspace title */}
      <div className="app-sidebar-workspace">
        WORKSPACE
      </div>

      {/* Navigation */}
      <nav className="app-sidebar-nav">

        {/* Dashboard */}
        <Link
          to="/dashboard"
          className={`app-sidebar-item ${
            activePage === "dashboard" ? "active" : ""
          }`}
        >
          <LayoutDashboard size={21} />

          <span>Dashboard</span>

          {activePage === "dashboard" && (
            <span className="app-sidebar-active-dot" />
          )}
        </Link>


        {/* Alerts */}
        <Link
          to="/alerts"
          className={`app-sidebar-item ${
            activePage === "alerts" ? "active" : ""
          }`}
        >
          <Bell size={21} />

          <span>Alerts</span>

          {activePage === "alerts" && (
            <span className="app-sidebar-active-dot" />
          )}
        </Link>


        {/* Investigations */}
        <Link
          to="/investigations"
          className={`app-sidebar-item ${
            activePage === "investigations" ? "active" : ""
          }`}
        >
          <FolderSearch size={21} />

          <span>Investigations</span>

          {activePage === "investigations" && (
            <span className="app-sidebar-active-dot" />
          )}
        </Link>

      </nav>

    </aside>
  );
}