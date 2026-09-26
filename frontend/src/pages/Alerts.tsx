import { AlertCircle, ArrowRight, Search, ShieldCheck, TriangleAlert } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import Sidebar from "../components/Sidebar";
import { apiErrorMessage, getAlerts, type Alert } from "../services/api";
import "../styles/alerts.css";


export default function Alerts() {
  const navigate = useNavigate();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    getAlerts()
      .then((response) => active && setAlerts(response.alerts))
      .catch((requestError) => active && setError(apiErrorMessage(requestError)));
    return () => { active = false; };
  }, []);

  const visibleAlerts = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return alerts;
    return alerts.filter((alert) =>
      [alert.account, alert.alert_id, ...alert.patterns].some((value) => value.toLowerCase().includes(query))
    );
  }, [alerts, search]);

  const count = (level: string) => alerts.filter((alert) => alert.risk_level === level).length;
  const summaries = [
    { level: "CRITICAL", icon: AlertCircle },
    { level: "HIGH", icon: TriangleAlert },
    { level: "MEDIUM", icon: AlertCircle },
    { level: "LOW", icon: ShieldCheck },
  ];

  return (
    <div className="alerts-page">
      <Sidebar activePage="alerts" />
      <main className="alerts-main">
        <header className="alerts-header"><div className="alerts-header-title"><h1>Alerts</h1><p>Live risk results</p></div></header>
        <div className="alerts-content">
          {error ? <p role="alert" className="error-message">{error}</p> : null}
          <div className="alert-summary-grid">
            {summaries.map(({ level, icon: Icon }) => (
              <div className="alert-summary-card" key={level}>
                <div className="alert-summary-number">{count(level)}</div>
                <div className="alert-summary-label">alerts</div>
                <div className={`alert-summary-badge ${level.toLowerCase()}`}><Icon size={16} /><span>{level}</span></div>
              </div>
            ))}
          </div>

          <section className="flagged-accounts-card">
            <div className="flagged-card-header"><div className="flagged-card-title-area"><div><h2>Flagged accounts</h2><p>{alerts.length} current alerts</p></div></div></div>
            <div className="alerts-filters">
              <label className="alerts-table-search"><Search size={20} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search account or pattern" /></label>
            </div>
            <div className="alerts-table-wrapper">
              <table className="alerts-table">
                <thead><tr><th>ACCOUNT</th><th>RISK SCORE</th><th>RISK LEVEL</th><th>DETECTED PATTERNS</th><th>STATUS</th><th></th></tr></thead>
                <tbody>
                  {visibleAlerts.map((alert) => (
                    <tr key={alert.alert_id}>
                      <td><div className="alert-account-cell"><strong>{alert.account}</strong><span>{alert.alert_id}</span></div></td>
                      <td><div className="alert-risk-score"><strong>{alert.risk_score}</strong><div className="alert-score-bar"><div className={`alert-score-fill ${alert.risk_level.toLowerCase()}`} style={{ width: `${alert.risk_score}%` }} /></div></div></td>
                      <td><span className={`alert-risk-badge ${alert.risk_level.toLowerCase()}`}>{alert.risk_level}</span></td>
                      <td><div className="alert-patterns">{alert.patterns.map((pattern) => <span className="alert-pattern-tag" key={pattern}>{pattern.split("_").join(" ")}</span>)}</div></td>
                      <td><span className="alert-status-badge new">{alert.status}</span></td>
                      <td><button className="alert-investigate-button" onClick={() => navigate(`/investigations/${alert.account}`)}>Investigate <ArrowRight size={17} /></button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {!error && visibleAlerts.length === 0 ? <p>No matching alerts.</p> : null}
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}
