import { AlertTriangle, ArrowLeftRight, Bell, IndianRupee, Users } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import Sidebar from "../components/Sidebar";
import { apiErrorMessage, getAlerts, getStats, type Alert, type DatasetStats } from "../services/api";
import "../styles/dashboard.css";


export default function Dashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState<DatasetStats | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [statsError, setStatsError] = useState("");
  const [alertsError, setAlertsError] = useState("");
  const [alertsLoading, setAlertsLoading] = useState(true);

  useEffect(() => {
    let active = true;
    getStats()
      .then((nextStats) => active && setStats(nextStats))
      .catch((requestError) => active && setStatsError(apiErrorMessage(requestError)));

    getAlerts()
      .then((nextAlerts) => active && setAlerts(nextAlerts.alerts))
      .catch((requestError) => active && setAlertsError(apiErrorMessage(requestError)))
      .finally(() => active && setAlertsLoading(false));

    return () => { active = false; };
  }, []);

  const highRisk = alerts.filter((alert) => ["HIGH", "CRITICAL"].includes(alert.risk_level)).length;
  const accountReferences = (stats?.dataset.unique_senders ?? 0) + (stats?.dataset.unique_receivers ?? 0);

  const kpis = [
    { title: "Account references", value: accountReferences.toLocaleString("en-IN"), icon: Users },
    { title: "Transactions", value: (stats?.dataset.total_transactions ?? 0).toLocaleString("en-IN"), icon: ArrowLeftRight },
    { title: "Total amount", value: `₹${(stats?.dataset.total_amount ?? 0).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`, icon: IndianRupee },
    { title: "High-risk alerts", value: highRisk.toLocaleString("en-IN"), icon: AlertTriangle },
  ];

  return (
    <div className="dashboard dark-dashboard">
      <Sidebar activePage="dashboard" />
      <main className="dashboard-main">
        <header className="dashboard-header">
          <div><h1>Dashboard</h1><p>Live data from Project Vigilance</p></div>
          <button className="header-icon" aria-label="Open alerts" onClick={() => navigate("/alerts")}>
            <Bell size={21} />
          </button>
        </header>

        <div className="dashboard-content">
          {statsError ? <p role="alert" className="error-message">{statsError}</p> : null}
          <section className="kpi-grid">
            {kpis.map(({ title, value, icon: Icon }) => (
              <div className="kpi-card" key={title}>
                <div className="kpi-top"><div className="kpi-icon blue"><Icon size={21} /></div></div>
                <div className="kpi-value">{value}</div>
                <div className="kpi-title">{title}</div>
              </div>
            ))}
          </section>

          <section className="chart-card">
            <div className="chart-header">
              <div><h2>Latest alerts</h2><p>Results from the detection and risk engines</p></div>
              <button className="filter-button" onClick={() => navigate("/alerts")}>View all alerts</button>
            </div>
            <div className="alerts-table-wrapper">
              <table className="alerts-table">
                <thead><tr><th>ACCOUNT</th><th>SCORE</th><th>RISK</th><th>PATTERNS</th></tr></thead>
                <tbody>
                  {alerts.slice(0, 5).map((alert) => (
                    <tr key={alert.alert_id} onClick={() => navigate(`/investigations/${alert.account}`)}>
                      <td>{alert.account}</td><td>{alert.risk_score}</td><td>{alert.risk_level}</td>
                      <td>{alert.patterns.join(", ") || "Behaviour score"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {alertsLoading ? <p>Detection is running. Dataset totals are ready above.</p> : null}
              {alertsError ? <p role="alert" className="error-message">{alertsError}</p> : null}
              {!alertsLoading && !alertsError && alerts.length === 0 ? <p>No alerts found.</p> : null}
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}
