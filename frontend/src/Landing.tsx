import React, { ChangeEvent, useState } from "react";
import axios from "axios";
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

      const response = await axios.post(
        `${API}/upload`,
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
          },
          timeout: 10 * 60 * 1000,
        }
      );

      setUploadResult(response.data);
    } catch (err: any) {
      console.error("Dataset upload failed:", err);

      if (err.response?.data?.detail) {
        const detail = err.response.data.detail;

        if (typeof detail === "string") {
          setError(detail);
        } else if (detail.message) {
          setError(detail.message);
        } else {
          setError("Dataset validation failed.");
        }
      } else if (err.code === "ECONNABORTED") {
        setError(
          "The upload timed out. Please check whether the backend is still processing the dataset."
        );
      } else {
        setError(
          "Unable to upload the dataset. Make sure the backend is running."
        );
      }
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="landing-page">

      {/* TOP BAR */}
      <header className="landing-topbar">

        <div className="landing-brand">

          <div className="landing-logo">
            V
          </div>

          <div>
            <div className="landing-brand-name">
              PROJECT VIGILANCE
            </div>

            <div className="landing-brand-subtitle">
              AI-Assisted AML Investigation Platform
            </div>
          </div>

        </div>

        <div className="landing-status">
          <span className="landing-status-dot"></span>
          SYSTEM READY
        </div>

      </header>


      {/* MAIN CONTENT */}
      <main className="landing-content">

        {/* HERO */}
        <section className="landing-hero">

          <div className="landing-eyebrow">
            AUTOMATED ANTI-MONEY LAUNDERING ANALYSIS
          </div>

          <h1>
            Detect suspicious activity.
            <br />
            <span>Understand the money trail.</span>
          </h1>

          <p className="landing-description">
            Project Vigilance helps investigators identify suspicious
            transaction patterns, assess entity risk, trace relationships,
            and understand why an entity was flagged.
          </p>

        </section>


        {/* USE CASES */}
        <section className="landing-patterns">

          <div className="pattern-card">

            <div className="pattern-number">
              01
            </div>

            <h3>
              Structuring
            </h3>

            <p>
              Identify transaction splitting and potential smurfing
              behaviour.
            </p>

          </div>


          <div className="pattern-card">

            <div className="pattern-number">
              02
            </div>

            <h3>
              Layering
            </h3>

            <p>
              Detect suspicious movement of funds through multiple
              intermediary accounts.
            </p>

          </div>


          <div className="pattern-card">

            <div className="pattern-number">
              03
            </div>

            <h3>
              Mule Accounts
            </h3>

            <p>
              Identify accounts receiving and subsequently moving
              suspicious funds.
            </p>

          </div>


          <div className="pattern-card">

            <div className="pattern-number">
              04
            </div>

            <h3>
              Network Analysis
            </h3>

            <p>
              Discover relationships through accounts, devices,
              IP addresses and transaction flows.
            </p>

          </div>

        </section>


        {/* UPLOAD */}
        <section className="upload-section">

          <div className="upload-card">

            <div className="upload-header">

              <div>

                <div className="upload-label">
                  AUTOMATED ANALYSIS
                </div>

                <h2>
                  Upload transaction dataset
                </h2>

                <p>
                  Upload your transaction CSV or XLSX file to
                  begin the AML analysis workflow.
                </p>

              </div>

              <div className="upload-icon">
                ↑
              </div>

            </div>


            {/* FILE SELECT */}
            <label className="file-drop-zone">

              <input
                type="file"
                accept=".csv,.xlsx"
                onChange={handleFileChange}
                disabled={uploading}
              />

              <div className="drop-icon">
                +
              </div>

              {file ? (
                <>
                  <strong>
                    {file.name}
                  </strong>

                  <span>
                    {(file.size / (1024 * 1024)).toFixed(2)} MB
                  </span>
                </>
              ) : (
                <>
                  <strong>
                    Select transaction dataset
                  </strong>

                  <span>
                    CSV or XLSX files supported
                  </span>
                </>
              )}

            </label>


            {/* ERROR */}
            {error && (
              <div className="upload-error">
                {error}
              </div>
            )}


            {/* SUCCESS */}
            {uploadResult && (

              <div className="upload-success">

                <div className="success-title">
                  Dataset uploaded successfully
                </div>

                <div className="upload-summary">

                  <div>
                    <span>
                      Rows processed
                    </span>

                    <strong>
                      {uploadResult.rows_processed.toLocaleString()}
                    </strong>
                  </div>


                  <div>
                    <span>
                      Rows inserted
                    </span>

                    <strong>
                      {uploadResult.rows_inserted.toLocaleString()}
                    </strong>
                  </div>


                  <div>
                    <span>
                      Duplicate IDs
                    </span>

                    <strong>
                      {uploadResult.duplicate_transaction_ids.toLocaleString()}
                    </strong>
                  </div>


                  <div>
                    <span>
                      Processing time
                    </span>

                    <strong>
                      {uploadResult.processing_time_seconds}s
                    </strong>
                  </div>

                </div>

              </div>

            )}


            {/* BUTTON */}
            {!uploadResult ? (

              <button
                className="analysis-button"
                onClick={handleUpload}
                disabled={!file || uploading}
              >

                {uploading ? (
                  <>
                    <span className="button-spinner"></span>
                    Processing Dataset...
                  </>
                ) : (
                  <>
                    Start Automated Analysis
                    <span>→</span>
                  </>
                )}

              </button>

            ) : (

              <button
                className="analysis-button"
                onClick={onAnalysisComplete}
              >
                Open Investigation Dashboard
                <span>→</span>
              </button>

            )}


            <div className="upload-note">
              <span>●</span>
              Uploading a new dataset replaces the currently loaded dataset.
            </div>

          </div>

        </section>

      </main>


      {/* FOOTER */}
      <footer className="landing-footer">

        <span>
          PROJECT VIGILANCE
        </span>

        <span>
          AI-assisted investigation • Human analyst remains in control
        </span>

      </footer>

    </div>
  );
}

export default Landing;