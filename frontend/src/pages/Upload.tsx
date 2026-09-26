// Target path: frontend/src/pages/Upload.tsx
//
// File-picker screen. The actual upload call happens in Processing.tsx
// (this page just collects the file and navigates there) -- that's the
// file wired to the real backend, not this one.

import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import UploadCard from "../components/UploadCard";
import { LogoMark, TargetIcon, GaugeIcon, NetworkIcon } from "../components/Icons";

const FEATURES = [
  { icon: <TargetIcon size={18} />, title: "Pattern detection", description: "Structuring, layering, mule networks and crypto off-ramping." },
  { icon: <GaugeIcon size={18} />, title: "Explainable risk scores", description: "Every flag comes with the evidence behind it." },
  { icon: <NetworkIcon size={18} />, title: "Money-flow connections", description: "Trace funds across accounts, devices and wallets." },
];

export default function Upload() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);

  return (
    <div style={{ minHeight: "100vh" }}>
      <header style={{ display: "flex", alignItems: "center", gap: 12, padding: "24px 40px" }}>
        <LogoMark size={36} />
        <div>
          <div style={{ fontWeight: 700, fontSize: 16, lineHeight: 1.1 }}>Project Vigilance</div>
          <div style={{ fontSize: 11, letterSpacing: "0.06em", color: "var(--color-text-muted)" }}>AML INTELLIGENCE</div>
        </div>
      </header>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 48, maxWidth: 1180, margin: "40px auto", padding: "0 40px", alignItems: "start" }}>
        <div>
          <span className="badge-pill">
            <span className="badge-dot" />
            Financial crime investigation platform
          </span>
          <h1 style={{ fontSize: 44, lineHeight: 1.15, margin: "20px 0 16px" }}>
            Uncover money laundering <span style={{ color: "var(--color-primary)" }}>with clarity.</span>
          </h1>
          <p style={{ fontSize: 16, color: "var(--color-text-muted)", lineHeight: 1.6, marginBottom: 32 }}>
            Upload a transaction dataset and Project Vigilance screens every account for
            suspicious behaviour, scores risk, and gives investigators a clear,
            evidence-backed path from alert to report.
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            {FEATURES.map((f) => (
              <div key={f.title} style={{ display: "flex", gap: 14, alignItems: "flex-start" }}>
                <div className="icon-circle">{f.icon}</div>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 15 }}>{f.title}</div>
                  <div style={{ fontSize: 14, color: "var(--color-text-muted)" }}>{f.description}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="card" style={{ boxShadow: "var(--shadow-lg)" }}>
          <h2 style={{ fontSize: 18, marginBottom: 4 }}>Upload transaction dataset</h2>
          <p style={{ fontSize: 13, color: "var(--color-text-muted)", marginBottom: 20 }}>
            Accounts, transactions, channels, devices and locations.
          </p>
          <UploadCard file={file} onFileSelected={setFile} />
          <button
            onClick={() => navigate("/processing", { state: { file } })}
            disabled={!file}
            style={{ width: "100%", marginTop: 20, padding: "14px 0", fontSize: 15 }}
          >
            Upload & Process {"\u2192"}
          </button>
          <p style={{ fontSize: 12, color: "var(--color-text-muted)", marginTop: 12, textAlign: "center" }}>
            Large files (100k+ transactions) may take a few minutes to process.
          </p>
        </div>
      </div>
    </div>
  );
}
