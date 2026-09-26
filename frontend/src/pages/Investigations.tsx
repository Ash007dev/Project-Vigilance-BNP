import { Link, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  Bell,
  FolderSearch,
  Search,
  Sun,
  ChevronDown,
  ShieldAlert,
  ArrowRight,
} from "lucide-react";

import "../styles/investigations.css";

const investigationCases = [
  {
    account: "ACC-33987",
    customer: "CUST-588171",
    score: 85,
    level: "Critical",
    patterns: ["Circular Money Flow", "Structuring", "Layering"],
    transactions: 48,
    status: "Under Investigation",
    detected: "20 Sep 2026, 01:21",
  },
  {
    account: "ACC-84023",
    customer: "CUST-743805",
    score: 69,
    level: "Medium",
    patterns: ["Structuring", "Shared Device/IP"],
    transactions: 135,
    status: "Under Investigation",
    detected: "09 Sep 2026, 05:06",
  },
  {
    account: "ACC-71204",
    customer: "CUST-937814",
    score: 41,
    level: "Low",
    patterns: ["Crypto Off-Ramping"],
    transactions: 124,
    status: "Under Investigation",
    detected: "15 Sep 2026, 00:06",
  },
];

export default function Investigations() {
  const navigate = useNavigate();

  const openInvestigation = (account: string) => {
    console.log("Opening investigation:", account);

    // For now, all Investigate buttons open the investigation dashboard.
    // Later we can pass the account ID and show account-specific details.
    navigate(`/investigations/${account}`);
  };

  return (
    <div className="investigations-page">

      {/* =====================================================
          SIDEBAR
      ====================================================== */}

      <aside className="investigations-sidebar">


        {/* Workspace */}
        <div className="investigations-workspace-title">
          WORKSPACE
        </div>

        <nav className="investigations-navigation">

          <Link
            to="/dashboard"
            className="investigations-nav-item"
          >
            <LayoutDashboard size={21} />
            <span>Dashboard</span>
          </Link>

          <Link
            to="/alerts"
            className="investigations-nav-item"
          >
            <Bell size={21} />
            <span>Alerts</span>
          </Link>

          <Link
            to="/investigations"
            className="investigations-nav-item active"
          >
            <FolderSearch size={21} />
            <span>Investigations</span>

            <span className="investigation-active-dot"></span>
          </Link>

        </nav>
      </aside>


      {/* =====================================================
          MAIN CONTENT
      ====================================================== */}

      <main className="investigations-main">

        {/* HEADER */}

        <header className="investigations-header">

          <div className="investigations-header-title">

            <h1>Investigations</h1>

            <p>
              Dataset · Project_Vigilance_Dataset_Password_Protected.xlsx
            </p>

          </div>

          <div className="investigations-header-right">

            {/* Search */}
            <div className="investigations-header-search">
              <Search size={20} />

              <input
                type="text"
                placeholder="Search account ID..."
              />
            </div>

            {/* Notification */}
            <button className="investigation-header-icon">
              <Bell size={21} />

              <span className="notification-dot"></span>
            </button>

            {/* Theme */}
            <button className="investigation-header-icon">
              <Sun size={21} />
            </button>

          </div>

        </header>


        {/* =====================================================
            INVESTIGATION CASES CARD
        ====================================================== */}

        <section className="investigation-cases-card">

          {/* Card header */}

          <div className="investigation-card-header">

            <div className="investigation-card-title-area">

              <div className="investigation-card-icon">
                <FolderSearch size={22} />
              </div>

              <div>
                <h2>Investigation cases</h2>

                <p>
                  Select a case to open its investigation dashboard
                </p>
              </div>

            </div>


            {/* Status tabs */}

            <div className="investigation-status-tabs">

              <button className="investigation-tab active">
                In progress
              </button>

              <button className="investigation-tab">
                New
              </button>

              <button className="investigation-tab">
                Resolved
              </button>

            </div>

          </div>


          {/* =====================================================
              TABLE
          ====================================================== */}

          <div className="investigation-table-wrapper">

            <table className="investigation-table">

              <thead>
                <tr>
                  <th>ACCOUNT</th>
                  <th>RISK SCORE</th>
                  <th>RISK LEVEL</th>
                  <th>DETECTED PATTERNS</th>
                  <th>STATUS</th>
                  <th>DETECTED</th>
                  <th></th>
                </tr>
              </thead>

              <tbody>

                {investigationCases.map((item) => (

                  <tr key={item.account}>

                    {/* Account */}

                    <td>
                      <div className="investigation-account">
                        <strong>{item.account}</strong>
                        <span>{item.customer}</span>
                      </div>
                    </td>


                    {/* Risk score */}

                    <td>
                      <div className="risk-score-cell">

                        <strong>{item.score}</strong>

                        <div className="risk-score-bar">
                          <div
                            className={`risk-score-fill ${item.level.toLowerCase()}`}
                            style={{
                              width: `${item.score}%`,
                            }}
                          ></div>
                        </div>

                      </div>
                    </td>


                    {/* Risk level */}

                    <td>
                      <span
                        className={`investigation-risk-badge ${item.level.toLowerCase()}`}
                      >
                        <span className="risk-badge-icon">
                          {item.level === "Critical" && "!"}
                          {item.level === "Medium" && "!"}
                          {item.level === "Low" && "✓"}
                        </span>

                        {item.level}
                      </span>
                    </td>


                    {/* Patterns */}

                    <td>
                      <div className="pattern-list">

                        {item.patterns.map((pattern) => (
                          <span
                            className="pattern-tag"
                            key={pattern}
                          >
                            {pattern}
                          </span>
                        ))}

                      </div>
                    </td>





                    {/* Status */}

                    <td>
                      <span className="investigation-status-badge">
                        <span></span>
                        {item.status}
                      </span>
                    </td>


                    {/* Detected */}

                    <td>
                      <span className="detected-date">
                        {item.detected}
                      </span>
                    </td>


                    {/* Investigate */}

                    <td>
                      <button
                        className="investigate-button"
                        onClick={() =>
                          openInvestigation(item.account)
                        }
                      >
                        Investigate
                        <ArrowRight size={17} />
                      </button>
                    </td>

                  </tr>

                ))}

              </tbody>

            </table>

          </div>

        </section>

      </main>

    </div>
  );
}