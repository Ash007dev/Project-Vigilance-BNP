import React, { useEffect, useState } from "react";
import axios from "axios";
import "./App.css";
import Investigation from "./Investigation";

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

  currencies: {
    currency: string;
    transaction_count: number;
    total_amount: number;
  }[];

  channels: {
    channel: string;
    transaction_count: number;
    total_amount: number;
  }[];

  crypto: {
    crypto_transactions: number;
    unique_crypto_wallets: number;
  };

  network: {
    shared_devices: number;
    shared_ips: number;
  };
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

  // Currently selected investigation entity
  const [selectedAccount, setSelectedAccount] = useState<string | null>(null);

  useEffect(() => {
    loadDashboard();
  }, []);

  async function loadDashboard() {
    try {
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
    (alert) =>
      alert.risk_level === "HIGH" ||
      alert.risk_level === "CRITICAL"
  ).length;

  const critical = alerts.filter(
    (alert) => alert.risk_level === "CRITICAL"
  ).length;

  /*
   * ---------------------------------------------------------
   * INVESTIGATION VIEW
   * ---------------------------------------------------------
   *
   * When an investigator selects an alert, show the
   * Investigation component instead of the dashboard.
   */
  if (selectedAccount) {
    return (
      <Investigation
        account={selectedAccount}
        onBack={() => setSelectedAccount(null)}
      />
    );
  }

  /*
   * ---------------------------------------------------------
   * LOADING
   * ---------------------------------------------------------
   */

  if (loading) {
    return (
      <div className="app">
        <div className="loading">
          Loading Project Vigilance...
        </div>
      </div>
    );
  }

  /*
   * ---------------------------------------------------------
   * DASHBOARD
   * ---------------------------------------------------------
   */

  return (
    <div className="app">
      <header className="topbar">
        <div>
          <div className="eyebrow">
            PROJECT VIGILANCE
          </div>

          <h1>
            AML Investigation Platform
          </h1>

          <p>
            Detect suspicious financial networks and reconstruct
            the investigation story.
          </p>
        </div>

        <div className="system-status">
          <span className="status-dot"></span>
          SYSTEM READY
        </div>
      </header>

      <main>

        {/* =====================================================
            TOP METRICS
        ====================================================== */}

        <section className="metrics">

          <MetricCard
            title="Total Transactions"
            value={
              stats?.dataset.total_transactions ?? 0
            }
          />

          <MetricCard
            title="Suspicious Alerts"
            value={alerts.length}
          />

          <MetricCard
            title="High Risk"
            value={highRisk}
          />

          <MetricCard
            title="Critical"
            value={critical}
          />

        </section>


        {/* =====================================================
            DATASET + WORKFLOW
        ====================================================== */}

        <section className="overview-grid">

          {/* Dataset Overview */}

          <div className="panel">

            <div className="panel-header">

              <div>
                <span className="panel-label">
                  DATASET
                </span>

                <h2>
                  Transaction Overview
                </h2>
              </div>

            </div>

            <div className="overview-stats">

              <div>
                <span>
                  Unique Senders
                </span>

                <strong>
                  {stats?.dataset.unique_senders ?? 0}
                </strong>
              </div>


              <div>
                <span>
                  Unique Receivers
                </span>

                <strong>
                  {stats?.dataset.unique_receivers ?? 0}
                </strong>
              </div>


              <div>
                <span>
                  Crypto Transactions
                </span>

                <strong>
                  {stats?.crypto?.crypto_transactions ?? 0}
                </strong>
              </div>


              <div>
                <span>
                  Total Amount
                </span>

                <strong>
                  ₹
                  {(stats?.dataset.total_amount ?? 0).toLocaleString(
                    "en-IN",
                    {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    }
                  )}
                </strong>
              </div>

            </div>

          </div>


          {/* Investigation Workflow */}

          <div className="panel workflow-panel">

            <span className="panel-label">
              INVESTIGATION WORKFLOW
            </span>

            <div className="workflow">

              <WorkflowStep
                number="01"
                label="Upload"
              />

              <WorkflowArrow />

              <WorkflowStep
                number="02"
                label="Detect"
              />

              <WorkflowArrow />

              <WorkflowStep
                number="03"
                label="Score"
              />

              <WorkflowArrow />

              <button
                className="workflow-step workflow-button"
                onClick={() => {
                  if (alerts.length > 0) {
                    setSelectedAccount(
                      alerts[0].account
                    );
                  }
                }}
              >
                <span>04</span>
                <strong>Investigate</strong>
              </button>

              <WorkflowArrow />

              <WorkflowStep
                number="05"
                label="Report"
              />

            </div>

          </div>

        </section>


        {/* =====================================================
            AML ALERT QUEUE
        ====================================================== */}

        <section className="panel alerts-panel">

          <div className="panel-header">

            <div>
              <span className="panel-label">
                AML ALERTS
              </span>

              <h2>
                Investigation Queue
              </h2>
            </div>

            <span className="alert-count">
              {alerts.length} ACTIVE
            </span>

          </div>


          {alerts.length === 0 ? (

            <div className="empty-state">
              No suspicious entities detected.
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
                    <th>Pattern</th>
                    <th>Status</th>
                    <th></th>
                  </tr>

                </thead>


                <tbody>

                  {alerts.map((alert) => (

                    <tr key={alert.alert_id}>

                      {/* Alert ID */}

                      <td className="alert-id">
                        {alert.alert_id}
                      </td>


                      {/* Entity */}

                      <td className="entity">
                        {alert.account}
                      </td>


                      {/* Risk Score */}

                      <td>

                        <strong>
                          {alert.risk_score}
                        </strong>

                        <span className="score-max">
                          {" "}
                          / 100
                        </span>

                      </td>


                      {/* Risk Level */}

                      <td>
                        <RiskBadge
                          level={alert.risk_level}
                        />
                      </td>


                      {/* Patterns */}

                      <td>

                        <div className="patterns">

                          {alert.patterns.map(
                            (pattern) => (

                              <span
                                key={pattern}
                                className="pattern"
                              >
                                {pattern.replaceAll(
                                  "_",
                                  " "
                                )}
                              </span>

                            )
                          )}

                        </div>

                      </td>


                      {/* Status */}

                      <td>

                        <span className="status-open">
                          {alert.status}
                        </span>

                      </td>


                      {/* Investigation Button */}

                      <td>

                        <button
                          className="investigate-btn"
                          onClick={() =>
                            setSelectedAccount(
                              alert.account
                            )
                          }
                        >
                          INVESTIGATE →
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


/* ============================================================
   METRIC CARD
============================================================ */

function MetricCard({
  title,
  value,
}: {
  title: string;
  value: number;
}) {
  return (
    <div className="metric-card">

      <span>
        {title}
      </span>

      <strong>
        {value.toLocaleString("en-IN")}
      </strong>

    </div>
  );
}


/* ============================================================
   RISK BADGE
============================================================ */

function RiskBadge({
  level,
}: {
  level: string;
}) {
  return (
    <span
      className={`risk-badge risk-${level.toLowerCase()}`}
    >
      {level}
    </span>
  );
}


/* ============================================================
   WORKFLOW STEP
============================================================ */

function WorkflowStep({
  number,
  label,
}: {
  number: string;
  label: string;
}) {
  return (
    <div className="workflow-step">

      <span>
        {number}
      </span>

      <strong>
        {label}
      </strong>

    </div>
  );
}


/* ============================================================
   WORKFLOW ARROW
============================================================ */

function WorkflowArrow() {
  return (
    <div className="workflow-arrow">
      →
    </div>
  );
}


export default App;