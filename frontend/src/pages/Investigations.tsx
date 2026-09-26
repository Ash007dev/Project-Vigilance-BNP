import { ArrowRight, FolderSearch, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import Sidebar from "../components/Sidebar";
import { apiErrorMessage, getAlerts, type Alert } from "../services/api";
import "../styles/investigations.css";


export default function Investigations() {
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
    return query ? alerts.filter((alert) => alert.account.toLowerCase().includes(query)) : alerts;
  }, [alerts, search]);

  return (
    <div className="investigations-page">
      <Sidebar activePage="investigations" />
      <main className="investigations-main">
        <header className="investigations-header">
          <div className="investigations-header-title"><h1>Investigations</h1><p>Open an account to review its evidence and graph</p></div>
          <label className="investigations-header-search"><Search size={20} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search account ID" /></label>
        </header>

        {error ? <p role="alert" className="error-message">{error}</p> : null}
        <section className="investigation-cases-card">
          <div className="investigation-card-header">
            <div className="investigation-card-title-area"><div className="investigation-card-icon"><FolderSearch size={22} /></div><div><h2>Investigation cases</h2><p>{alerts.length} current cases</p></div></div>
          </div>
          <div className="investigation-table-wrapper">
            <table className="investigation-table">
              <thead><tr><th>ACCOUNT</th><th>RISK SCORE</th><th>RISK LEVEL</th><th>DETECTED PATTERNS</th><th>STATUS</th><th></th></tr></thead>
              <tbody>
                {visibleAlerts.map((alert) => (
                  <tr key={alert.alert_id}>
                    <td><div className="investigation-account"><strong>{alert.account}</strong><span>{alert.alert_id}</span></div></td>
                    <td><div className="risk-score-cell"><strong>{alert.risk_score}</strong><div className="risk-score-bar"><div className={`risk-score-fill ${alert.risk_level.toLowerCase()}`} style={{ width: `${alert.risk_score}%` }} /></div></div></td>
                    <td><span className={`investigation-risk-badge ${alert.risk_level.toLowerCase()}`}>{alert.risk_level}</span></td>
                    <td><div className="pattern-list">{alert.patterns.map((pattern) => <span className="pattern-tag" key={pattern}>{pattern.split("_").join(" ")}</span>)}</div></td>
                    <td><span className="investigation-status-badge">{alert.status}</span></td>
                    <td><button className="investigate-button" onClick={() => navigate(`/investigations/${alert.account}`)}>Investigate <ArrowRight size={17} /></button></td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!error && visibleAlerts.length === 0 ? <p>No matching investigations.</p> : null}
          </div>
        </section>
      </main>
    </div>
  );
}
