import React, { ChangeEvent, useState } from "react";
import axios from "axios";
import {
  Activity,
  ArrowRight,
  CheckCircle2,
  FileSpreadsheet,
  Network,
  Search,
  ShieldCheck,
  UploadCloud,
  UsersRound,
} from "lucide-react";
import "./Landing.css";

const API = "http://localhost:8000/api";

interface UploadResult {
  status: string;
  filename: string;
  rows_processed: number;
  rows_inserted: number;
  columns: string[];
  processing_time_seconds: number;
  duplicate_transaction_ids: number;
}

interface LandingProps {
  onAnalysisComplete: () => void;
}

function Landing({ onAnalysisComplete }: LandingProps) {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);
  const [error, setError] = useState("");

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0] || null;
    setFile(selectedFile);
    setUploadResult(null);
    setError("");
  };

  const handleUpload = async () => {
    if (!file) {
      setError("Please select a CSV or XLSX transaction dataset.");
      return;
    }

    setUploading(true);
    setError("");
    setUploadResult(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await axios.post(`${API}/upload`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 10 * 60 * 1000,
      });

      setUploadResult(response.data);
    } catch (err: any) {
      console.error("Dataset upload failed:", err);

      if (err.response?.data?.detail) {
        const detail = err.response.data.detail;
        setError(
          typeof detail === "string"
            ? detail
            : detail.message || "Dataset validation failed."
        );
      } else if (err.code === "ECONNABORTED") {
        setError("The upload timed out. Please check whether the backend is still processing the dataset.");
      } else {
        setError("Unable to upload the dataset. Make sure the backend is running.");
      }
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="landing-page">
      <header className="landing-topbar">
        <div className="landing-brand">
          <div className="landing-logo">V</div>
          <div>
            <div className="landing-brand-name">PROJECT VIGILANCE</div>
            <div className="landing-brand-subtitle">AI-Assisted AML Investigation Platform</div>
          </div>
        </div>

        <div className="landing-status">
          <span className="landing-status-dot" />
          SYSTEM READY
        </div>
      </header>

      <main className="landing-content">
        <section className="landing-hero">
          <div className="landing-eyebrow">
            <span className="hero-rule" />
            INTELLIGENT FINANCIAL CRIME INVESTIGATION
          </div>

          <h1>
            Detect suspicious activity.
            <br />
            <span>Understand the money trail.</span>
          </h1>

          <p className="landing-description">
            Project Vigilance combines transaction analytics, risk intelligence,
            relationship graphs and AI-assisted explanations to help investigators
            understand suspicious financial activity faster.
          </p>

          <div className="hero-proof">
            <span><ShieldCheck size={15} /> Evidence-led</span>
            <span><Network size={15} /> Network-aware</span>
            <span><Activity size={15} /> Investigator-focused</span>
          </div>
        </section>

        <section className="landing-patterns" aria-label="Core capabilities">
          <PatternCard icon={<Search />} number="01" title="Structuring" text="Identify fragmented transaction behaviour and threshold-splitting patterns." />
          <PatternCard icon={<Network />} number="02" title="Layering" text="Trace movement of funds across intermediary accounts and transaction chains." />
          <PatternCard icon={<UsersRound />} number="03" title="Mule Accounts" text="Surface high-velocity accounts receiving and forwarding suspicious funds." />
          <PatternCard icon={<Activity />} number="04" title="Network Analysis" text="Connect accounts, devices, IPs, wallets and transaction flows into one view." />
        </section>

        <section className="upload-section">
          <div className="upload-card">
            <div className="upload-header">
              <div>
                <div className="upload-label">START INVESTIGATION</div>
                <h2>Upload transaction dataset</h2>
                <p>Import a CSV or XLSX dataset and begin the automated AML analysis workflow.</p>
              </div>
              <div className="upload-icon"><UploadCloud size={21} /></div>
            </div>

            <label className={`file-drop-zone ${file ? "has-file" : ""}`}>
              <input
                type="file"
                accept=".csv,.xlsx"
                onChange={handleFileChange}
                disabled={uploading}
              />
              <div className="drop-icon">
                {file ? <FileSpreadsheet size={22} /> : <UploadCloud size={22} />}
              </div>
              {file ? (
                <>
                  <strong>{file.name}</strong>
                  <span>{(file.size / (1024 * 1024)).toFixed(2)} MB · Ready for analysis</span>
                </>
              ) : (
                <>
                  <strong>Select transaction dataset</strong>
                  <span>CSV or XLSX · Drop a file here or browse</span>
                </>
              )}
            </label>

            {error && (
              <div className="upload-error">
                <span>!</span>{error}
              </div>
            )}

            {uploading && (
              <div className="upload-processing">
                <div className="processing-spinner" />
                <div>
                  <strong>Processing dataset</strong>
                  <span>Validating transactions and preparing the investigation workspace…</span>
                </div>
              </div>
            )}

            {uploadResult && (
              <div className="upload-success">
                <div className="success-title">
                  <CheckCircle2 size={18} />
                  Dataset processed successfully
                </div>
                <div className="upload-summary">
                  <div><span>Rows processed</span><strong>{uploadResult.rows_processed.toLocaleString()}</strong></div>
                  <div><span>Rows inserted</span><strong>{uploadResult.rows_inserted.toLocaleString()}</strong></div>
                  <div><span>Duplicate IDs</span><strong>{uploadResult.duplicate_transaction_ids.toLocaleString()}</strong></div>
                  <div><span>Processing time</span><strong>{uploadResult.processing_time_seconds}s</strong></div>
                </div>
              </div>
            )}

            {!uploadResult ? (
              <button className="analysis-button" onClick={handleUpload} disabled={!file || uploading}>
                {uploading ? "Analyzing dataset…" : "Start automated analysis"}
                {!uploading && <ArrowRight size={17} />}
              </button>
            ) : (
              <button className="analysis-button" onClick={onAnalysisComplete}>
                Open investigation dashboard <ArrowRight size={17} />
              </button>
            )}

            <div className="upload-note">
              <span><ShieldCheck size={13} /></span>
              Uploading a new dataset replaces the currently loaded dataset.
            </div>
          </div>
        </section>
      </main>

      <footer className="landing-footer">
        <span>PROJECT VIGILANCE</span>
        <span>AI-assisted investigation · Human analyst remains in control</span>
      </footer>
    </div>
  );
}

function PatternCard({
  icon,
  number,
  title,
  text,
}: {
  icon: React.ReactNode;
  number: string;
  title: string;
  text: string;
}) {
  return (
    <article className="pattern-card">
      <div className="pattern-top">
        <span className="pattern-number">{number}</span>
        <span className="pattern-icon">{icon}</span>
      </div>
      <h3>{title}</h3>
      <p>{text}</p>
    </article>
  );
}

export default Landing;
