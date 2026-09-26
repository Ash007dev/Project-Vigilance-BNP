import React from "react";
import ReactDOM from "react-dom/client";
import "./styles.css";

function App() {
  return (
    <main className="app">
      <header>
        <div>
          <p className="eyebrow">PROJECT VIGILANCE</p>
          <h1>AML Investigation Platform</h1>
          <p className="subtitle">
            Detect suspicious financial networks and reconstruct the investigation story.
          </p>
        </div>
        <div className="status">SYSTEM READY</div>
      </header>

      <section className="cards">
        <div className="card"><span>Total Transactions</span><strong>—</strong></div>
        <div className="card"><span>Suspicious</span><strong>—</strong></div>
        <div className="card"><span>High Risk</span><strong>—</strong></div>
        <div className="card"><span>Critical</span><strong>—</strong></div>
      </section>

      <section className="panel">
        <h2>Investigation workflow</h2>
        <div className="workflow">
          <div>Upload</div><span>→</span><div>Detect</div><span>→</span>
          <div>Score</div><span>→</span><div>Investigate</div><span>→</span>
          <div>Report</div>
        </div>
      </section>
    </main>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode><App /></React.StrictMode>
);
