// Target path: frontend/src/pages/Processing.tsx
//
// NOW WIRED TO THE REAL BACKEND. Two real changes from the mock version,
// not just the import swap:
//
// 1. Removed the artificial "minimum display time" padding. That existed
//    because mock data resolved almost instantly and needed padding to
//    feel real. The real backend's upload time is genuinely variable --
//    seconds for a small file, a few minutes for 100k+ transactions (see
//    app/risk/features.py's known performance profile) -- so there's
//    nothing to pad; we just wait for the real response.
// 2. Added a visible elapsed-time counter and a message for long uploads,
//    since silently sitting on "Scoring accounts" for 2+ minutes with no
//    feedback reads as broken even when it's working correctly.

import React, { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { uploadTransactions, ApiError } from "../services/api";

const STEPS = [
  "Parsing transaction dataset",
  "Extracting behavioural features",
  "Running AML pattern rules",
  "Scoring accounts",
];

const LONG_UPLOAD_WARNING_SECONDS = 20;

export default function Processing() {
  const location = useLocation();
  const navigate = useNavigate();
  const file = (location.state as { file?: File } | null)?.file ?? null;

  const [currentStep, setCurrentStep] = useState(0);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!file) {
      navigate("/upload");
      return;
    }

    const stepTimer = setInterval(() => {
      setCurrentStep((s) => Math.min(s + 1, STEPS.length - 1));
    }, 700);

    const elapsedTimer = setInterval(() => {
      setElapsedSeconds((s) => s + 1);
    }, 1000);

    uploadTransactions(file)
      .then(() => navigate("/dashboard"))
      .catch((err) =>
        setError(err instanceof ApiError ? err.message : "Upload failed. Check the backend is running.")
      )
      .finally(() => {
        clearInterval(stepTimer);
        clearInterval(elapsedTimer);
      });

    return () => {
      clearInterval(stepTimer);
      clearInterval(elapsedTimer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ width: 380, textAlign: "center" }}>
        {error ? (
          <>
            <p style={{ color: "var(--color-critical)", marginBottom: 16 }}>{error}</p>
            <button onClick={() => navigate("/upload")}>Back to Upload</button>
          </>
        ) : (
          <>
            <div className="spinner" style={{ margin: "0 auto 24px" }} />
            <ul style={{ listStyle: "none", padding: 0, textAlign: "left" }}>
              {STEPS.map((step, i) => (
                <li
                  key={step}
                  style={{
                    display: "flex", alignItems: "center", gap: 10, padding: "8px 0",
                    color: i <= currentStep ? "var(--color-text)" : "var(--color-text-muted)",
                    fontWeight: i === currentStep ? 600 : 400,
                  }}
                >
                  <span>{i < currentStep ? "\u2705" : i === currentStep ? "\u23F3" : "\u25CB"}</span>
                  {step}
                </li>
              ))}
            </ul>

            <div style={{ marginTop: 16, fontSize: 12, color: "var(--color-text-muted)" }}>
              {elapsedSeconds}s elapsed
            </div>

            {elapsedSeconds >= LONG_UPLOAD_WARNING_SECONDS && (
              <p style={{ marginTop: 12, fontSize: 13, color: "var(--color-text-muted)" }}>
                Large datasets can take a few minutes to fully process. Still working -- no need to refresh.
              </p>
            )}
          </>
        )}
      </div>
    </div>
  );
}
