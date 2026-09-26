import React, { useEffect, useState } from "react";
import axios from "axios";
import "./Investigation.css";
import RelationshipGraph from "./RelationshipGraph";

const API = "http://localhost:8000/api";

type InvestigationData = {
  status: string;

  entity: {
    account: string;
    risk_score: number;
    risk_level: string;
  };

  patterns: string[];

  reasons: {
    pattern: string;
    points: number;
    reason: string;
  }[];

  transactions: any[];
  timeline: any[];

  relationships: {
    accounts: string[];
    devices: string[];
    ips: string[];
    crypto_wallets: string[];
  };

  summary: {
    transaction_count: number;
    connected_account_count: number;
    device_count: number;
    ip_count: number;
    crypto_wallet_count: number;
  };
};

type AIExplanationData = {
  status: string;
  entity: string;
  risk_score: number;
  risk_level: string;
  patterns: string[];

  evidence: any;

  ai: {
    success: boolean;
    model?: string;
    explanation?: string;
    error?: string;
    details?: string;
  };
};

type Props = {
  account: string;
  onBack: () => void;
};

export default function Investigation({
  account,
  onBack,
}: Props) {
  const [data, setData] =
    useState<InvestigationData | null>(null);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");

  // ---------------------------------------------------------
  // AI STATE
  // ---------------------------------------------------------

  const [aiData, setAiData] =
    useState<AIExplanationData | null>(null);

  const [aiLoading, setAiLoading] =
    useState(true);

  const [aiError, setAiError] =
    useState("");

  // ---------------------------------------------------------
  // LOAD INVESTIGATION
  // ---------------------------------------------------------

  useEffect(() => {

    const loadInvestigation = async () => {

      try {

        setLoading(true);
        setError("");

        const response =
          await axios.get<InvestigationData>(
            `${API}/investigations/${encodeURIComponent(account)}`
          );

        console.log(
          "Investigation API response:",
          response.data
        );

        setData(response.data);

      } catch (err: any) {

        console.error(
          "Investigation API error:",
          err
        );

        setError(
          err?.response?.data?.detail ||
            err?.message ||
            "Failed to load investigation."
        );

      } finally {

        setLoading(false);

      }
    };

    loadInvestigation();

  }, [account]);

  // ---------------------------------------------------------
  // LOAD AI EXPLANATION
  // ---------------------------------------------------------

  useEffect(() => {

    const loadAIExplanation = async () => {

      try {

        setAiLoading(true);
        setAiError("");
        setAiData(null);

        const response =
          await axios.get<AIExplanationData>(
            `${API}/ai/explanation/${encodeURIComponent(account)}`
          );

        console.log(
          "AI Explanation API response:",
          response.data
        );

        setAiData(response.data);

      } catch (err: any) {

        console.error(
          "AI Explanation API error:",
          err
        );

        setAiError(
          err?.response?.data?.detail ||
            err?.message ||
            "Failed to generate AI explanation."
        );

      } finally {

        setAiLoading(false);

      }
    };

    loadAIExplanation();

  }, [account]);

  // ---------------------------------------------------------
  // LOADING
  // ---------------------------------------------------------

  if (loading) {

    return (
      <div className="dashboard">

        <button onClick={onBack}>
          ← Back
        </button>

        <div className="card">

          <h2>
            Loading Investigation...
          </h2>

          <p>
            Analyzing {account}
          </p>

        </div>

      </div>
    );
  }

  // ---------------------------------------------------------
  // ERROR
  // ---------------------------------------------------------

  if (error) {

    return (
      <div className="dashboard">

        <button onClick={onBack}>
          ← Back
        </button>

        <div className="card">

          <h2>
            Investigation Error
          </h2>

          <p>
            {error}
          </p>

        </div>

      </div>
    );
  }

  // ---------------------------------------------------------
  // NO DATA
  // ---------------------------------------------------------

  if (!data || !data.entity) {

    return (
      <div className="dashboard">

        <button onClick={onBack}>
          ← Back
        </button>

        <div className="card">

          <h2>
            No investigation data
          </h2>

          <p>
            The API returned an unexpected response.
          </p>

        </div>

      </div>
    );
  }

  const {
    entity,
    patterns,
    reasons,
    transactions,
    timeline,
    relationships,
  } = data;

  // ---------------------------------------------------------
  // FORMAT AI EXPLANATION
  // ---------------------------------------------------------

  const formatAIExplanation = (
    explanation: string
  ) => {

    const sections = [
      "EXECUTIVE SUMMARY",
      "WHY FLAGGED",
      "KEY EVIDENCE",
      "NETWORK ANALYSIS",
      "TIMELINE ANALYSIS",
      "INVESTIGATOR FOCUS",
      "LIMITATIONS",
    ];

    let formatted = explanation;

    sections.forEach((section) => {

      formatted = formatted.replace(
        new RegExp(section, "g"),
        `\n\n${section}\n`
      );

    });

    return formatted.trim();
  };

  // ---------------------------------------------------------
  // RENDER
  // ---------------------------------------------------------

  return (
    <div className="dashboard">

      {/* =====================================================
          HEADER
      ===================================================== */}

      <div className="dashboard-header">

        <div>

          <button onClick={onBack}>
            ← Back to Dashboard
          </button>

          <h1>
            Investigation
          </h1>

          <p>
            Investigating entity:{" "}
            <strong>
              {entity.account}
            </strong>
          </p>

        </div>

      </div>


      {/* =====================================================
          RISK OVERVIEW
      ===================================================== */}

      <div className="metrics-grid">

        <div className="metric-card">

          <span>
            Risk Score
          </span>

          <strong>
            {entity.risk_score}/100
          </strong>

        </div>


        <div className="metric-card">

          <span>
            Risk Level
          </span>

          <strong>
            {entity.risk_level}
          </strong>

        </div>


        <div className="metric-card">

          <span>
            Transactions
          </span>

          <strong>
            {data.summary.transaction_count}
          </strong>

        </div>


        <div className="metric-card">

          <span>
            Connected Accounts
          </span>

          <strong>
            {data.summary.connected_account_count}
          </strong>

        </div>

      </div>


      {/* =====================================================
          ENTITY OVERVIEW
      ===================================================== */}

      <div className="card">

        <h2>
          Entity Overview
        </h2>

        <p>
          <strong>
            Account:
          </strong>{" "}
          {entity.account}
        </p>

        <p>
          <strong>
            Risk Score:
          </strong>{" "}
          {entity.risk_score}
        </p>

        <p>
          <strong>
            Risk Level:
          </strong>{" "}
          {entity.risk_level}
        </p>

      </div>


      {/* =====================================================
          DETECTED PATTERNS
      ===================================================== */}

      <div className="card">

        <h2>
          Detected AML Patterns
        </h2>

        {patterns.length === 0 ? (

          <p>
            No patterns detected.
          </p>

        ) : (

          <div>

            {patterns.map((pattern) => (

              <span
                key={pattern}
                style={{
                  display: "inline-block",
                  marginRight: "10px",
                  marginBottom: "10px",
                  padding: "8px 12px",
                  borderRadius: "6px",
                  background: "#fee2e2",
                  fontWeight: 600,
                }}
              >
                {pattern}
              </span>

            ))}

          </div>

        )}

      </div>


      {/* =====================================================
          RISK REASONS
      ===================================================== */}

      <div className="card">

        <h2>
          Why Was This Entity Flagged?
        </h2>

        {reasons.length === 0 ? (

          <p>
            No specific risk reasons available.
          </p>

        ) : (

          reasons.map((item, index) => (

            <div
              key={`${item.pattern}-${index}`}
              style={{
                padding: "15px",
                marginBottom: "10px",
                border: "1px solid #ddd",
                borderRadius: "8px",
              }}
            >

              <strong>
                {item.pattern}
              </strong>

              <p>
                <strong>
                  Risk contribution:
                </strong>{" "}
                +{item.points}
              </p>

              <p>
                {item.reason}
              </p>

            </div>

          ))

        )}

      </div>


      {/* =====================================================
          AI INVESTIGATION EXPLANATION
      ===================================================== */}

      <div className="card ai-explanation-card">

        <div className="ai-explanation-header">

          <div>

            <h2>AI Investigation Explanation</h2>

            <p className="ai-explanation-subtitle">
              AI-assisted analysis based on detected evidence
            </p>

          </div>

          {aiData?.ai?.model && (
            <span className="ai-model-badge">
              {aiData.ai.model}
            </span>
          )}

        </div>


        {/* AI LOADING */}

        {aiLoading && (

          <div className="ai-loading">

            <h3>
              Generating AI Explanation...
            </h3>

            <p>
              The AI is analyzing the risk evidence,
              transaction activity, and network relationships.
            </p>

          </div>

        )}


        {/* AI ERROR */}

        {!aiLoading && aiError && (

          <div className="ai-error">

            <strong>
              AI explanation unavailable
            </strong>

            <p>
              {aiError}
            </p>

          </div>

        )}


        {/* AI RESPONSE ERROR */}

        {!aiLoading &&
          !aiError &&
          aiData &&
          !aiData.ai.success && (

            <div className="ai-response">

              <strong>
                AI explanation generation failed
              </strong>

              <p>
                {aiData.ai.error}
              </p>

              {aiData.ai.details && (
                <small>
                  {aiData.ai.details}
                </small>
              )}

            </div>

          )}


        {/* AI RESPONSE */}

        {!aiLoading &&
          !aiError &&
          aiData &&
          aiData.ai.success &&
          aiData.ai.explanation && (

            <div className="ai-response">

              {formatAIExplanation(
                aiData.ai.explanation
              )}

            </div>

          )}


        <div className="ai-disclaimer">

          AI-generated analysis is provided as
          investigator assistance and does not constitute
          a final compliance or legal decision.

        </div>

      </div>


      {/* =====================================================
          RELATIONSHIP GRAPH
      ===================================================== */}

      <RelationshipGraph
        account={entity.account}
      />


      {/* =====================================================
          RELATIONSHIPS
      ===================================================== */}

      <div className="card">

        <h2>
          Relationships
        </h2>

        <h3>
          Connected Accounts (
          {relationships.accounts.length}
          )
        </h3>

        <div>

          {relationships.accounts.length === 0 ? (

            <p>
              No connected accounts found.
            </p>

          ) : (

            relationships.accounts.map(
              (relatedAccount) => (

                <span
                  key={relatedAccount}
                  style={{
                    display: "inline-block",
                    margin: "4px",
                    padding: "6px 10px",
                    background: "#eef2ff",
                    borderRadius: "5px",
                  }}
                >
                  {relatedAccount}
                </span>

              )
            )

          )}

        </div>


        <h3>
          Devices (
          {relationships.devices.length}
          )
        </h3>

        {relationships.devices.length === 0 ? (

          <p>
            No shared devices found.
          </p>

        ) : (

          relationships.devices.map(
            (device) => (
              <p key={device}>
                {device}
              </p>
            )
          )

        )}


        <h3>
          IP Addresses (
          {relationships.ips.length}
          )
        </h3>

        {relationships.ips.length === 0 ? (

          <p>
            No shared IP addresses found.
          </p>

        ) : (

          relationships.ips.map(
            (ip) => (
              <p key={ip}>
                {ip}
              </p>
            )
          )

        )}


        <h3>
          Crypto Wallets (
          {relationships.crypto_wallets.length}
          )
        </h3>

        {relationships.crypto_wallets.length === 0 ? (

          <p>
            No crypto wallets connected to this entity.
          </p>

        ) : (

          relationships.crypto_wallets.map(
            (wallet) => (
              <p key={wallet}>
                {wallet}
              </p>
            )
          )

        )}

      </div>


      {/* =====================================================
          TIMELINE
      ===================================================== */}

      <div className="card">

        <h2>
          Transaction Timeline
        </h2>

        <div
          style={{
            overflowX: "auto",
          }}
        >

          <table>

            <thead>

              <tr>

                <th>
                  Time
                </th>

                <th>
                  Transaction
                </th>

                <th>
                  Sender
                </th>

                <th>
                  Receiver
                </th>

                <th>
                  Amount
                </th>

                <th>
                  Currency
                </th>

                <th>
                  Channel
                </th>

              </tr>

            </thead>


            <tbody>

              {timeline.map(
                (tx, index) => (

                  <tr
                    key={`${tx.transaction_id}-${index}`}
                  >

                    <td>
                      {new Date(
                        tx.timestamp
                      ).toLocaleString()}
                    </td>

                    <td>
                      {tx.transaction_id}
                    </td>

                    <td>
                      {tx.sender_account}
                    </td>

                    <td>
                      {tx.receiver_account}
                    </td>

                    <td>
                      {Number(
                        tx.amount
                      ).toLocaleString()}
                    </td>

                    <td>
                      {tx.currency}
                    </td>

                    <td>
                      {tx.channel}
                    </td>

                  </tr>

                )
              )}

            </tbody>

          </table>

        </div>

      </div>


      {/* =====================================================
          TRANSACTION DETAILS
      ===================================================== */}

      <div className="card">

        <h2>
          Transactions ({transactions.length})
        </h2>

        <div
          style={{
            overflowX: "auto",
          }}
        >

          <table>

            <thead>

              <tr>

                <th>
                  Transaction ID
                </th>

                <th>
                  Sender
                </th>

                <th>
                  Receiver
                </th>

                <th>
                  Amount
                </th>

                <th>
                  Currency
                </th>

                <th>
                  Device
                </th>

                <th>
                  IP
                </th>

              </tr>

            </thead>


            <tbody>

              {transactions.map(
                (tx, index) => (

                  <tr
                    key={`${tx.transaction_id}-${index}`}
                  >

                    <td>
                      {tx.transaction_id}
                    </td>

                    <td>
                      {tx.sender_account}
                    </td>

                    <td>
                      {tx.receiver_account}
                    </td>

                    <td>
                      {Number(
                        tx.amount
                      ).toLocaleString()}
                    </td>

                    <td>
                      {tx.currency}
                    </td>

                    <td>
                      {tx.device_id || "-"}
                    </td>

                    <td>
                      {tx.ip_address || "-"}
                    </td>

                  </tr>

                )
              )}

            </tbody>

          </table>

        </div>

      </div>


      {/* =====================================================
          INVESTIGATION SUMMARY
      ===================================================== */}

      <div className="card">

        <h2>
          Investigation Summary
        </h2>

        <p>
          This entity has a risk score of{" "}
          <strong>
            {entity.risk_score}/100
          </strong>{" "}
          and is currently classified as{" "}
          <strong>
            {entity.risk_level}
          </strong>.
        </p>

        <p>
          The investigation identified{" "}
          <strong>
            {data.summary.transaction_count}
          </strong>{" "}
          transactions involving{" "}
          <strong>
            {data.summary.connected_account_count}
          </strong>{" "}
          connected accounts.
        </p>

        <p>
          The entity is also associated with{" "}
          <strong>
            {data.summary.device_count}
          </strong>{" "}
          device and{" "}
          <strong>
            {data.summary.ip_count}
          </strong>{" "}
          IP address.
        </p>

      </div>

    </div>
  );
}