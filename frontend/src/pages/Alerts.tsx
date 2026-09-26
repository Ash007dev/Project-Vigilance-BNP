import { useNavigate, Link } from "react-router-dom";
import {
  LayoutDashboard,
  Bell,
  FolderSearch,
  Search,
  Sun,
  ChevronDown,
  ShieldAlert,
  ArrowRight,
  AlertCircle,
  TriangleAlert,
  CircleAlert,
  ShieldCheck,
  ChevronDown as ChevronDownIcon,
} from "lucide-react";

import "../styles/alerts.css";

const alertData = [
  {
    account: "ACC-27719",
    customer: "CUST-656889",
    score: 93,
    riskLevel: "Critical",
    patterns: [
      "Mule Behavior",
      "Structuring",
      "Circular Money Flow",
    ],
    transactions: 161,
    amount: "₹73.9 L",
    status: "New",
    detected: "19 Sep 2026, 10:54",
  },
  {
    account: "ACC-33987",
    customer: "CUST-588171",
    score: 85,
    riskLevel: "Critical",
    patterns: [
      "Circular Money Flow",
      "Structuring",
      "Layering",
    ],
    transactions: 48,
    amount: "₹66.6 L",
    status: "Under Investigation",
    detected: "20 Sep 2026, 01:21",
  },
  {
    account: "ACC-18820",
    customer: "CUST-194388",
    score: 78,
    riskLevel: "High",
    patterns: [
      "Layering",
      "Structuring",
    ],
    transactions: 134,
    amount: "₹28.0 L",
    status: "New",
    detected: "24 Sep 2026, 11:59",
  },
  {
    account: "ACC-84023",
    customer: "CUST-743805",
    score: 69,
    riskLevel: "Medium",
    patterns: [
      "Structuring",
      "Shared Device/IP",
    ],
    transactions: 135,
    amount: "₹92.8 L",
    status: "Under Investigation",
    detected: "09 Sep 2026, 05:06",
  },
  {
    account: "ACC-40219",
    customer: "CUST-550865",
    score: 61,
    riskLevel: "Medium",
    patterns: [
      "Structuring",
    ],
    transactions: 170,
    amount: "₹69.3 L",
    status: "Resolved",
    detected: "20 Sep 2026, 19:09",
  },
];

export default function Alerts() {
  const navigate = useNavigate();

  const handleInvestigate = (account: string) => {
    navigate(`/investigations/${account}`);
  };

  return (
    <div className="alerts-page">

      {/* =====================================================
          SIDEBAR
      ====================================================== */}

      <aside className="alerts-sidebar">    



        {/* Workspace */}

        <div className="alerts-workspace-title">
          WORKSPACE
        </div>


        {/* Navigation */}

        <nav className="alerts-navigation">

          <Link
            to="/dashboard"
            className="alerts-nav-item"
          >
            <LayoutDashboard size={21} />

            <span>
              Dashboard
            </span>
          </Link>


          <Link
            to="/alerts"
            className="alerts-nav-item active"
          >
            <Bell size={21} />

            <span>
              Alerts
            </span>
          </Link>


          <Link
            to="/investigations"
            className="alerts-nav-item"
          >
            <FolderSearch size={21} />

            <span>
              Investigations
            </span>
          </Link>

        </nav>

      </aside>


      {/* =====================================================
          MAIN CONTENT
      ====================================================== */}

      <main className="alerts-main">

        {/* =====================================================
            HEADER
        ====================================================== */}

        <header className="alerts-header">

          <div className="alerts-header-title">

            <h1>
              Alerts
            </h1>

            <p>
              Dataset · Project_Vigilance_Dataset_Password_Protected.xlsx
            </p>

          </div>


          <div className="alerts-header-right">



            {/* Notification */}




            {/* Theme */}

            <button
              type="button"
              className="alerts-header-icon"
            >
              <Sun size={21} />
            </button>


          </div>

        </header>


        {/* =====================================================
            CONTENT
        ====================================================== */}

        <div className="alerts-content">


          {/* ===================================================
              SUMMARY CARDS
          ==================================================== */}

          <div className="alert-summary-grid">


            {/* Critical */}

            <div className="alert-summary-card">

              <div className="alert-summary-number">
                2
              </div>

              <div className="alert-summary-label">
                alerts
              </div>

              <div className="alert-summary-badge critical">

                <AlertCircle size={16} />

                <span>
                  Critical
                </span>

              </div>

            </div>


            {/* High */}

            <div className="alert-summary-card">

              <div className="alert-summary-number">
                1
              </div>

              <div className="alert-summary-label">
                alerts
              </div>

              <div className="alert-summary-badge high">

                <TriangleAlert size={16} />

                <span>
                  High
                </span>

              </div>

            </div>


            {/* Medium */}

            <div className="alert-summary-card">

              <div className="alert-summary-number">
                8
              </div>

              <div className="alert-summary-label">
                alerts
              </div>

              <div className="alert-summary-badge medium">

                <CircleAlert size={16} />

                <span>
                  Medium
                </span>

              </div>

            </div>


            {/* Low */}

            <div className="alert-summary-card">

              <div className="alert-summary-number">
                3
              </div>

              <div className="alert-summary-label">
                alerts
              </div>

              <div className="alert-summary-badge low">

                <ShieldCheck size={16} />

                <span>
                  Low
                </span>

              </div>

            </div>

          </div>


          {/* ===================================================
              FLAGGED ACCOUNTS
          ==================================================== */}

          <section className="flagged-accounts-card">


            {/* Card heading */}

            <div className="flagged-card-header">

              <div className="flagged-card-title-area">

                <div className="flagged-card-icon">
                  <ShieldAlert size={22} />
                </div>

                <div>

                  <h2>
                    Flagged accounts
                  </h2>

                  <p>
                    14 alerts from the detection engine · select a row for details
                  </p>

                </div>

              </div>

            </div>


            {/* =================================================
                FILTERS
            ================================================== */}

            <div className="alerts-filters">

              {/* Search */}

              <div className="alerts-table-search">

                <Search size={20} />

                <input
                  type="text"
                  placeholder="Search account, customer..."
                />

              </div>


              {/* Risk */}

              <button
                type="button"
                className="alerts-filter-button"
              >

                <span>
                  All risk levels
                </span>

                <ChevronDownIcon size={18} />

              </button>


              {/* Status */}

              <button
                type="button"
                className="alerts-filter-button"
              >

                <span>
                  All statuses
                </span>

                <ChevronDownIcon size={18} />

              </button>


              {/* Pattern */}

              <button
                type="button"
                className="alerts-filter-button"
              >

                <span>
                  All patterns
                </span>

                <ChevronDownIcon size={18} />

              </button>

            </div>


            {/* =================================================
                TABLE
            ================================================== */}

            <div className="alerts-table-wrapper">

              <table className="alerts-table">

                <thead>

                  <tr>

                    <th>
                      ACCOUNT
                    </th>

                    <th>
                      RISK SCORE
                    </th>

                    <th>
                      RISK LEVEL
                    </th>

                    <th>
                      DETECTED PATTERNS
                    </th>

                    <th>
                      TXNS
                    </th>

                    <th>
                      AMOUNT
                    </th>

                    <th>
                      STATUS
                    </th>

                    <th>
                      DETECTED
                    </th>

                    <th>
                    </th>

                  </tr>

                </thead>


                <tbody>

                  {alertData.map((alert) => (

                    <tr key={alert.account}>


                      {/* Account */}

                      <td>

                        <div className="alert-account-cell">

                          <strong>
                            {alert.account}
                          </strong>

                          <span>
                            {alert.customer}
                          </span>

                        </div>

                      </td>


                      {/* Risk score */}

                      <td>

                        <div className="alert-risk-score">

                          <strong>
                            {alert.score}
                          </strong>

                          <div className="alert-score-bar">

                            <div
                              className={`alert-score-fill ${alert.riskLevel.toLowerCase()}`}
                              style={{
                                width: `${alert.score}%`,
                              }}
                            />

                          </div>

                        </div>

                      </td>


                      {/* Risk level */}

                      <td>

                        <span
                          className={`alert-risk-badge ${alert.riskLevel.toLowerCase()}`}
                        >

                          {alert.riskLevel === "Critical" && (
                            <AlertCircle size={15} />
                          )}

                          {alert.riskLevel === "High" && (
                            <TriangleAlert size={15} />
                          )}

                          {alert.riskLevel === "Medium" && (
                            <CircleAlert size={15} />
                          )}

                          {alert.riskLevel === "Low" && (
                            <ShieldCheck size={15} />
                          )}

                          {alert.riskLevel}

                        </span>

                      </td>


                      {/* Patterns */}

                      <td>

                        <div className="alert-patterns">

                          {alert.patterns.map((pattern) => (

                            <span
                              key={pattern}
                              className="alert-pattern-tag"
                            >
                              {pattern}
                            </span>

                          ))}

                        </div>

                      </td>


                      {/* Transactions */}

                      <td>

                        <span className="alert-table-number">
                          {alert.transactions}
                        </span>

                      </td>


                      {/* Amount */}

                      <td>

                        <span className="alert-table-amount">
                          {alert.amount}
                        </span>

                      </td>


                      {/* Status */}

                      <td>

                        <span
                          className={`alert-status-badge ${
                            alert.status === "New"
                              ? "new"
                              : alert.status === "Resolved"
                              ? "resolved"
                              : "investigating"
                          }`}
                        >

                          <span></span>

                          {alert.status}

                        </span>

                      </td>


                      {/* Detected */}

                      <td>

                        <span className="alert-detected-date">
                          {alert.detected}
                        </span>

                      </td>


                      {/* Investigate */}

                      <td>

                        <button
                          type="button"
                          className="alert-investigate-button"
                          onClick={() =>
                            handleInvestigate(alert.account)
                          }
                        >

                          <span>
                            Investigate
                          </span>

                          <ArrowRight size={17} />

                        </button>

                      </td>

                    </tr>

                  ))}

                </tbody>

              </table>

            </div>

          </section>

        </div>

      </main>

    </div>
  );
}