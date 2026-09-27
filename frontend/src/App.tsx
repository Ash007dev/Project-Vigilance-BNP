import React, { useEffect, useState } from "react";
import axios from "axios";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  BarChart3,
  CircleDot,
  FileSearch,
  Network,
  ShieldAlert,
  UploadCloud,
} from "lucide-react";
import "./App.css";
import Investigation from "./Investigation";
import Landing from "./Landing";

const API = "http://localhost:8000/api";

type Stats = {
  dataset: {
    total_transactions: number;
    unique_senders: number;
    unique_receivers: number;
    total_amount: number;
    average_amount: number;
    minimum_amount: number;
    maximum_amount: number;
    first_transaction: string;
    last_transaction: string;
  };
  currencies: { currency: string; transaction_count: number; total_amount: number }[];
  channels: { channel: string; transaction_count: number; total_amount: number }[];
  crypto: { crypto_transactions: number; unique_crypto_wallets: number };
  network: { shared_devices: number; shared_ips: number };
};

type Alert = {
  alert_id: string;
  account: string;
  risk_score: number;
  risk_level: string;
  patterns: string[];
  status: string;
};

function App() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [showLanding, setShowLanding] = useState(true);
  const [selectedAccount, setSelectedAccount] = useState<string | null>(null);

  useEffect(() => {
    if (!showLanding) loadDashboard();
  }, [showLanding]);

  async function loadDashboard() {
    try {
      setLoading(true);
      const [statsResponse, alertsResponse] = await Promise.all([
        axios.get(`${API}/stats`),
        axios.get(`${API}/alerts`),
      ]);
      setStats(statsResponse.data);
      setAlerts(alertsResponse.data.alerts || []);
    } catch (error) {
      console.error("Failed to load dashboard:", error);
    } finally {
      setLoading(false);
    }
  }

  const highRisk = alerts.filter(
    (a) => a.risk_level === "HIGH" || a.risk_level === "CRITICAL"
  ).length;

  const critical = alerts.filter((a) => a.risk_level === "CRITICAL").length;

  if (showLanding) {
    return <Landing onAnalysisComplete={() => setShowLanding(false)} />;
  }

  if (selectedAccount) {
    return (
      <Investigation
        account={selectedAccount}
        onBack={() => setSelectedAccount(null)}
      />
    );
  }

  if (loading) {
    return (
      <div className="app-shell app-loading-shell">
        <LoadingScreen
          eyebrow="PROJECT VIGILANCE"
          title="Preparing investigation workspace"
          description="Loading the latest transaction intelligence and AML alerts."
        />
      </div>
    );
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar-copy">
          <div className="brand-lockup">
            <div className="brand-mark" aria-hidden="true">V</div>
            <div>
              <div className="eyebrow">PROJECT VIGILANCE</div>
              <h1>AML Investigation Platform</h1>
              <p>
                Detect suspicious financial networks and reconstruct the
                investigation story.
              </p>
            </div>
          </div>
        </div>

        <div className="system-status" aria-label="System ready">
          <span className="status-dot" />
          <span>SYSTEM READY</span>
        </div>
      </header>

      <main className="dashboard-main">
        <section className="metrics" aria-label="Key investigation metrics">
          <MetricCard icon={<BarChart3 />} title="Total Transactions" value={stats?.dataset.total_transactions ?? 0} />
          <MetricCard icon={<AlertTriangle />} title="Suspicious Alerts" value={alerts.length} accent="warning" />
          <MetricCard icon={<ShieldAlert />} title="High Risk" value={highRisk} accent="danger" />
          <MetricCard icon={<CircleDot />} title="Critical" value={critical} accent="critical" />
        </section>

        <section className="overview-grid">
          <div className="panel dataset-panel">
            <div className="panel-header">
              <div>
                <span className="panel-label">DATASET</span>
                <h2>Transaction Overview</h2>
              </div>
              <div className="panel-icon"><Activity size={18} /></div>
            </div>

            <div className="overview-stats">
              <OverviewStat label="Unique Senders" value={stats?.dataset.unique_senders ?? 0} />
              <OverviewStat label="Unique Receivers" value={stats?.dataset.unique_receivers ?? 0} />
              <OverviewStat label="Crypto Transactions" value={stats?.crypto?.crypto_transactions ?? 0} />
              <OverviewStat
                label="Total Amount"
                value={`₹${(stats?.dataset.total_amount ?? 0).toLocaleString("en-IN", {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}`}
              />
            </div>
          </div>

          <div className="panel workflow-panel">
            <div className="workflow-header">
              <div>
                <span className="panel-label">INVESTIGATION WORKFLOW</span>
                <h2>Case Progression</h2>
              </div>
              <span className="workflow-meta">05 STEPS</span>
            </div>

            <div className="workflow">
              <WorkflowStep number="01" label="Upload" icon={<UploadCloud size={17} />} />
              <WorkflowArrow />
              <WorkflowStep number="02" label="Detect" icon={<FileSearch size={17} />} />
              <WorkflowArrow />
              <WorkflowStep number="03" label="Score" icon={<BarChart3 size={17} />} />
              <WorkflowArrow />
              <button
                type="button"
                className="workflow-step workflow-button is-active"
                onClick={() => alerts.length > 0 && setSelectedAccount(alerts[0].account)}
                disabled={alerts.length === 0}
              >
                <span className="workflow-number">04</span>
                <span className="workflow-icon"><Network size={17} /></span>
                <strong>Investigate</strong>
                <small>OPEN CASE</small>
              </button>
              <WorkflowArrow />
              <WorkflowStep number="05" label="Report" icon={<FileSearch size={17} />} />
            </div>
          </div>
        </section>

        <section className="panel alerts-panel">
          <div className="panel-header">
            <div>
              <span className="panel-label">AML ALERTS</span>
              <h2>Investigation Queue</h2>
            </div>
            <span className="alert-count">{alerts.length} ACTIVE</span>
          </div>

          {alerts.length === 0 ? (
            <div className="empty-state">
              <ShieldAlert size={24} />
              <strong>No suspicious entities detected</strong>
              <span>The current dataset has no active AML alerts.</span>
            </div>
          ) : (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Alert</th>
                    <th>Entity</th>
                    <th>Risk Score</th>
                    <th>Risk Level</th>
                    <th>Detected Pattern</th>
                    <th>Status</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {alerts.map((alert) => (
                    <tr key={alert.alert_id}>
                      <td className="alert-id">{alert.alert_id}</td>
                      <td className="entity">{alert.account}</td>
                      <td>
                        <strong>{alert.risk_score}</strong>
                        <span className="score-max"> / 100</span>
                      </td>
                      <td><RiskBadge level={alert.risk_level} /></td>
                      <td>
                        <div className="patterns">
                          {alert.patterns.map((pattern) => (
                            <span key={pattern} className="pattern">
                              {pattern.replaceAll("_", " ")}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td><span className="status-open">{alert.status}</span></td>
                      <td>
                        <button
                          type="button"
                          className="investigate-btn"
                          onClick={() => setSelectedAccount(alert.account)}
                        >
                          Investigate <ArrowRight size={15} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

function LoadingScreen({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description: string;
}) {
  return (
    <div className="loading-screen">
      <div className="loading-orbit" aria-hidden="true">
        <div className="loading-core">V</div>
      </div>
      <span className="loading-eyebrow">{eyebrow}</span>
      <h1>{title}</h1>
      <p>{description}</p>
      <div className="loading-progress"><span /></div>
      <span className="loading-status">SECURE ANALYSIS PIPELINE · INITIALIZING</span>
    </div>
  );
}

function MetricCard({
  icon,
  title,
  value,
  accent = "default",
}: {
  icon: React.ReactNode;
  title: string;
  value: number;
  accent?: string;
}) {
  return (
    <div className={`metric-card metric-${accent}`}>
      <div className="metric-icon">{icon}</div>
      <span className="metric-label">{title}</span>
      <strong>{value.toLocaleString("en-IN")}</strong>
    </div>
  );
}

function OverviewStat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="overview-stat">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function RiskBadge({ level }: { level: string }) {
  return <span className={`risk-badge risk-${level.toLowerCase()}`}>{level}</span>;
}

function WorkflowStep({
  number,
  label,
  icon,
}: {
  number: string;
  label: string;
  icon: React.ReactNode;
}) {
  return (
    <div className="workflow-step">
      <span className="workflow-number">{number}</span>
      <span className="workflow-icon">{icon}</span>
      <strong>{label}</strong>
    </div>
  );
}

function WorkflowArrow() {
  return <div className="workflow-arrow" aria-hidden="true"><ArrowRight size={15} /></div>;
}

export default App;
