import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  ChevronDown,
  ChevronUp,
  CircleAlert,
  Clock3,
  Download,
  FileText,
  Globe2,
  Network,
  Server,
  ShieldAlert,
  Sparkles,
  WalletCards,
} from "lucide-react";
import "./Investigation.css";
import RelationshipGraph from "./RelationshipGraph";

const API = "http://localhost:8000/api";

type InvestigationData = {
  status: string;
  entity: { account: string; risk_score: number; risk_level: string };
  patterns: string[];
  reasons: { pattern: string; points: number; reason: string }[];
  transactions: any[];
  timeline: any[];
  relationships: { accounts: string[]; devices: string[]; ips: string[]; crypto_wallets: string[] };
  summary: { transaction_count: number; connected_account_count: number; device_count: number; ip_count: number; crypto_wallet_count: number };
};

type AIExplanationData = {
  status: string;
  entity: string;
  risk_score: number;
  risk_level: string;
  patterns: string[];
  evidence: any;
  ai: { success: boolean; model?: string; explanation?: string; error?: string; details?: string };
};

type Props = { account: string; onBack: () => void };

const AI_SECTIONS = [
  "EXECUTIVE SUMMARY",
  "WHY FLAGGED",
  "KEY EVIDENCE",
  "NETWORK ANALYSIS",
  "TIMELINE ANALYSIS",
  "INVESTIGATOR FOCUS",
  "LIMITATIONS",
];

export default function Investigation({ account, onBack }: Props) {
  const [data, setData] = useState<InvestigationData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [aiData, setAiData] = useState<AIExplanationData | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState("");
  const [aiExpanded, setAiExpanded] = useState(false);
  const [reportLoading, setReportLoading] = useState(false);
  const [reportError, setReportError] = useState("");

  useEffect(() => {
    const loadInvestigation = async () => {
      try {
        setLoading(true);
        setError("");
        const response = await axios.get<InvestigationData>(
          `${API}/investigations/${encodeURIComponent(account)}`
        );
        setData(response.data);
      } catch (err: any) {
        console.error("Investigation API error:", err);
        setError(err?.response?.data?.detail || err?.message || "Failed to load investigation.");
      } finally {
        setLoading(false);
      }
    };
    loadInvestigation();
  }, [account]);

  useEffect(() => {
    if (!aiExpanded) return;

    const loadAIExplanation = async () => {
      try {
        setAiLoading(true);
        setAiError("");
        const response = await axios.get<AIExplanationData>(
          `${API}/ai/explanation/${encodeURIComponent(account)}`
        );
        setAiData(response.data);
      } catch (err: any) {
        console.error("AI Explanation API error:", err);
        setAiError(err?.response?.data?.detail || err?.message || "Failed to generate AI explanation.");
      } finally {
        setAiLoading(false);
      }
    };

    if (!aiData) loadAIExplanation();
  }, [account, aiExpanded, aiData]);

  const generateReport = async () => {
    try {
      setReportLoading(true);
      setReportError("");
      const response = await axios.get(
        `${API}/report/${encodeURIComponent(account)}`,
        { responseType: "blob", timeout: 10 * 60 * 1000 }
      );
      const blob = new Blob([response.data], { type: "application/pdf" });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `Project_Vigilance_${account}_Investigation_Report.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Report generation failed:", err);
      setReportError("Unable to generate the investigation report.");
    } finally {
      setReportLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="investigation-shell">
        <button className="back-button loading-back" onClick={onBack}><ArrowLeft size={15} /> Dashboard</button>
        <InvestigationLoading account={account} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="investigation-shell">
        <button className="back-button" onClick={onBack}><ArrowLeft size={15} /> Dashboard</button>
        <div className="investigation-state error-state">
          <CircleAlert size={30} />
          <h2>Investigation could not be loaded</h2>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  if (!data?.entity) {
    return (
      <div className="investigation-shell">
        <button className="back-button" onClick={onBack}><ArrowLeft size={15} /> Dashboard</button>
        <div className="investigation-state">
          <FileText size={30} />
          <h2>No investigation data</h2>
          <p>The API returned an unexpected response.</p>
        </div>
      </div>
    );
  }

  const { entity, patterns, reasons, transactions, timeline, relationships } = data;

  return (
    <div className="investigation-shell">
      <header className="investigation-header">
        <div className="investigation-header-left">
          <button className="back-button" onClick={onBack}>
            <ArrowLeft size={15} /> Back to dashboard
          </button>

          <div className="investigation-title-row">
            <div>
              <span className="section-kicker">CASE INVESTIGATION</span>
              <h1>Investigation</h1>
              <p>Entity <strong>{entity.account}</strong> · Evidence-led AML analysis</p>
            </div>
            <RiskBadge level={entity.risk_level} score={entity.risk_score} />
          </div>
        </div>

        <button className="report-button" onClick={generateReport} disabled={reportLoading}>
          {reportLoading ? <span className="button-spinner" /> : <Download size={16} />}
          {reportLoading ? "Generating report…" : "Export investigation report"}
        </button>
      </header>

      {reportError && <div className="report-error"><CircleAlert size={15} /> {reportError}</div>}

      <main className="investigation-content">
        <section className="investigation-metrics">
          <InvestigationMetric label="Risk score" value={`${entity.risk_score}/100`} icon={<ShieldAlert />} tone={entity.risk_level.toLowerCase()} />
          <InvestigationMetric label="Transactions" value={data.summary.transaction_count} icon={<Activity />} />
          <InvestigationMetric label="Connected accounts" value={data.summary.connected_account_count} icon={<Network />} />
          <InvestigationMetric label="Devices / IPs" value={`${data.summary.device_count} / ${data.summary.ip_count}`} icon={<Server />} />
        </section>

        <section className="case-grid">
          <div className="case-card">
            <div className="case-card-heading">
              <div>
                <span className="section-kicker">ENTITY OVERVIEW</span>
                <h2>Case identity</h2>
              </div>
              <span className="case-id">{entity.account}</span>
            </div>
            <div className="identity-grid">
              <IdentityItem label="Account" value={entity.account} />
              <IdentityItem label="Risk score" value={`${entity.risk_score} / 100`} />
              <IdentityItem label="Risk level" value={entity.risk_level} />
              <IdentityItem label="AML patterns" value={patterns.length} />
            </div>
          </div>

          <div className="case-card pattern-card-investigation">
            <div className="case-card-heading">
              <div>
                <span className="section-kicker">DETECTED SIGNALS</span>
                <h2>AML patterns</h2>
              </div>
              <span className="signal-count">{patterns.length}</span>
            </div>
            <div className="signal-list">
              {patterns.length === 0 ? (
                <span className="muted-copy">No patterns detected.</span>
              ) : (
                patterns.map((pattern) => (
                  <span className="signal-chip" key={pattern}>
                    <span className="signal-dot" />
                    {pattern.replaceAll("_", " ")}
                  </span>
                ))
              )}
            </div>
          </div>
        </section>

        <section className="case-card reasons-card">
          <div className="case-card-heading">
            <div>
              <span className="section-kicker">DETECTION EVIDENCE</span>
              <h2>Why was this entity flagged?</h2>
              <p>Each detection is isolated so the investigator can review the evidence and risk contribution independently.</p>
            </div>
          </div>

          <div className="reason-list">
            {reasons.length === 0 ? (
              <div className="muted-copy">No specific risk reasons available.</div>
            ) : (
              reasons.map((item, index) => (
                <article className={`reason-item reason-${getReasonTone(item.points)}`} key={`${item.pattern}-${index}`}>
                  <div className="reason-index">{String(index + 1).padStart(2, "0")}</div>
                  <div className="reason-main">
                    <div className="reason-title-row">
                      <div>
                        <span className="reason-label">DETECTION</span>
                        <h3>{item.pattern.replaceAll("_", " ")}</h3>
                      </div>
                      <span className="risk-contribution">+{item.points} risk</span>
                    </div>
                    <p>{item.reason}</p>
                  </div>
                </article>
              ))
            )}
          </div>
        </section>

        <section className={`ai-card ${aiExpanded ? "is-open" : ""}`}>
          <button
            type="button"
            className="ai-card-toggle"
            onClick={() => setAiExpanded((value) => !value)}
            aria-expanded={aiExpanded}
          >
            <div className="ai-heading">
              <div className="ai-icon"><Sparkles size={18} /></div>
              <div>
                <span className="section-kicker">AI ASSISTED ANALYSIS</span>
                <h2>Investigation explanation</h2>
                <p>Open to review a structured explanation grounded in the detected evidence.</p>
              </div>
            </div>
            <div className="ai-toggle-meta">
              {aiData?.ai?.model && <span>{aiData.ai.model}</span>}
              {aiExpanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
            </div>
          </button>

          {aiExpanded && (
            <div className="ai-content">
              {aiLoading && (
                <div className="ai-loading-state">
                  <div className="ai-pulse" />
                  <div>
                    <strong>Generating investigation explanation</strong>
                    <p>The AI is analyzing risk evidence, transaction activity and network relationships.</p>
                  </div>
                </div>
              )}

              {!aiLoading && aiError && (
                <div className="ai-message ai-message-error">
                  <CircleAlert size={18} />
                  <div><strong>AI explanation unavailable</strong><p>{aiError}</p></div>
                </div>
              )}

              {!aiLoading && !aiError && aiData?.ai && !aiData.ai.success && (
                <div className="ai-message ai-message-error">
                  <CircleAlert size={18} />
                  <div><strong>AI explanation generation failed</strong><p>{aiData.ai.error}</p>{aiData.ai.details && <small>{aiData.ai.details}</small>}</div>
                </div>
              )}

              {!aiLoading && !aiError && aiData?.ai?.success && aiData.ai.explanation && (
                <AIExplanation explanation={aiData.ai.explanation} />
              )}

              <div className="ai-disclaimer">
                AI-generated analysis is investigator assistance only and does not constitute a final compliance or legal decision.
              </div>
            </div>
          )}
        </section>

        <RelationshipGraph account={entity.account} />

        <section className="case-card relationships-card">
          <div className="case-card-heading">
            <div>
              <span className="section-kicker">CONNECTED ENTITIES</span>
              <h2>Relationships</h2>
            </div>
          </div>

          <RelationshipGroup icon={<Network />} title={`Accounts · ${relationships.accounts.length}`} items={relationships.accounts} />
          <RelationshipGroup icon={<Server />} title={`Devices · ${relationships.devices.length}`} items={relationships.devices} />
          <RelationshipGroup icon={<Globe2 />} title={`IP addresses · ${relationships.ips.length}`} items={relationships.ips} />
          <RelationshipGroup icon={<WalletCards />} title={`Crypto wallets · ${relationships.crypto_wallets.length}`} items={relationships.crypto_wallets} />
        </section>

        <DataTable title="Transaction timeline" kicker="CHRONOLOGY" icon={<Clock3 />} rows={timeline} timeline />
        <DataTable title={`Transactions · ${transactions.length}`} kicker="TRANSACTION RECORDS" icon={<FileText />} rows={transactions} />

        <section className="case-card summary-card">
          <div className="case-card-heading">
            <div>
              <span className="section-kicker">INVESTIGATION SUMMARY</span>
              <h2>Case synopsis</h2>
            </div>
          </div>
          <div className="summary-copy">
            <p>
              This entity has a risk score of <strong>{entity.risk_score}/100</strong> and is currently classified as <strong>{entity.risk_level}</strong>.
            </p>
            <p>
              The investigation identified <strong>{data.summary.transaction_count}</strong> transactions involving <strong>{data.summary.connected_account_count}</strong> connected accounts.
            </p>
            <p>
              The entity is associated with <strong>{data.summary.device_count}</strong> device(s) and <strong>{data.summary.ip_count}</strong> IP address(es).
            </p>
          </div>
        </section>
      </main>
    </div>
  );
}

function InvestigationLoading({ account }: { account: string }) {
  return (
    <div className="investigation-loading">
      <div className="investigation-loading-mark"><div>V</div></div>
      <span className="section-kicker">SECURE INVESTIGATION PIPELINE</span>
      <h1>Reconstructing the case</h1>
      <p>Analyzing <strong>{account}</strong> across transactions, risk signals and connected entities.</p>
      <div className="loading-track"><span /></div>
      <div className="loading-steps">
        <span><i className="is-done" /> Fetch case evidence</span>
        <span><i className="is-active" /> Analyze relationships</span>
        <span><i /> Prepare investigation view</span>
      </div>
    </div>
  );
}

function InvestigationMetric({ label, value, icon, tone = "" }: { label: string; value: React.ReactNode; icon: React.ReactNode; tone?: string }) {
  return (
    <div className={`investigation-metric ${tone}`}>
      <div className="investigation-metric-icon">{icon}</div>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function IdentityItem({ label, value }: { label: string; value: React.ReactNode }) {
  return <div className="identity-item"><span>{label}</span><strong>{value}</strong></div>;
}

function RiskBadge({ level, score }: { level: string; score: number }) {
  return (
    <div className={`case-risk risk-${level.toLowerCase()}`}>
      <span>RISK</span>
      <strong>{score}</strong>
      <small>{level}</small>
    </div>
  );
}

function getReasonTone(points: number) {
  if (points >= 30) return "critical";
  if (points >= 20) return "high";
  if (points >= 10) return "medium";
  return "low";
}

function RelationshipGroup({ icon, title, items }: { icon: React.ReactNode; title: string; items: string[] }) {
  return (
    <div className="relationship-group">
      <div className="relationship-group-title">{icon}<strong>{title}</strong></div>
      {items.length === 0 ? (
        <span className="muted-copy">None identified</span>
      ) : (
        <div className="relationship-items">
          {items.map((item) => <span key={item}>{item}</span>)}
        </div>
      )}
    </div>
  );
}

function AIExplanation({ explanation }: { explanation: string }) {
  const sections = useMemo(() => {
    const normalized = explanation.replace(/\r/g, "").trim();
    const regex = new RegExp(`(${AI_SECTIONS.join("|")})`, "g");
    const pieces = normalized.split(regex).filter(Boolean);
    const result: { title: string; body: string }[] = [];
    let current = "AI ANALYSIS";
    let body = "";
    for (const piece of pieces) {
      const clean = piece.trim();
      if (AI_SECTIONS.includes(clean)) {
        if (body.trim()) result.push({ title: current, body: body.trim() });
        current = clean;
        body = "";
      } else {
        body += `${piece}\n`;
      }
    }
    if (body.trim()) result.push({ title: current, body: body.trim() });
    return result;
  }, [explanation]);

  return (
    <div className="ai-sections">
      {sections.map((section) => (
        <article className="ai-section" key={section.title}>
          <div className="ai-section-title">{section.title}</div>
          <div className="ai-section-body">
            {section.body.split("\n").map((line, index) => {
              const trimmed = line.trim();
              if (!trimmed) return <div className="ai-spacer" key={index} />;
              const bullet = trimmed.match(/^[-*]\s+(.*)$/);
              const content = bullet ? bullet[1] : trimmed;
              return bullet ? (
                <div className="ai-bullet" key={index}><span />{renderBold(content)}</div>
              ) : (
                <p key={index}>{renderBold(content)}</p>
              );
            })}
          </div>
        </article>
      ))}
    </div>
  );
}

function renderBold(text: string) {
  const parts = text.split(/(\*\*.*?\*\*)/g);
  return parts.map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={index}>{part.slice(2, -2)}</strong>;
    }
    return <React.Fragment key={index}>{part}</React.Fragment>;
  });
}

function DataTable({ title, kicker, icon, rows, timeline = false }: { title: string; kicker: string; icon: React.ReactNode; rows: any[]; timeline?: boolean }) {
  return (
    <section className="case-card table-card">
      <div className="case-card-heading">
        <div className="table-title">
          <div className="table-icon">{icon}</div>
          <div>
            <span className="section-kicker">{kicker}</span>
            <h2>{title}</h2>
          </div>
        </div>
      </div>

      <div className="data-table-wrap">
        <table>
          <thead>
            <tr>
              {timeline ? (
                <>
                  <th>Time</th><th>Transaction</th><th>Sender</th><th>Receiver</th><th>Amount</th><th>Currency</th><th>Channel</th>
                </>
              ) : (
                <>
                  <th>Transaction ID</th><th>Sender</th><th>Receiver</th><th>Amount</th><th>Currency</th><th>Device</th><th>IP</th>
                </>
              )}
            </tr>
          </thead>
          <tbody>
            {rows.map((tx, index) => (
              <tr key={`${tx.transaction_id || "row"}-${index}`}>
                {timeline ? (
                  <>
                    <td>{tx.timestamp ? new Date(tx.timestamp).toLocaleString() : "-"}</td>
                    <td className="mono-cell">{tx.transaction_id}</td>
                    <td>{tx.sender_account}</td>
                    <td>{tx.receiver_account}</td>
                    <td>{Number(tx.amount).toLocaleString()}</td>
                    <td>{tx.currency}</td>
                    <td>{tx.channel}</td>
                  </>
                ) : (
                  <>
                    <td className="mono-cell">{tx.transaction_id}</td>
                    <td>{tx.sender_account}</td>
                    <td>{tx.receiver_account}</td>
                    <td>{Number(tx.amount).toLocaleString()}</td>
                    <td>{tx.currency}</td>
                    <td>{tx.device_id || "-"}</td>
                    <td>{tx.ip_address || "-"}</td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length === 0 && <div className="table-empty">No records available.</div>}
      </div>
    </section>
  );
}
