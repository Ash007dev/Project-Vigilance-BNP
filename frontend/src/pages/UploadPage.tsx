import { Moon, Sun } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import ProcessingCard from "../components/ProcessingCard";
import UploadCard from "../components/UploadCard";
import FeatureList from "../components/FeatureList";
import { apiErrorMessage, uploadDataset } from "../services/api";
import "../styles/app.css";


export default function UploadPage() {
  const navigate = useNavigate();
  const [dark, setDark] = useState(true);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState("");

  async function handleStartProcessing(file: File) {
    setSelectedFile(file);
    setProcessing(true);
    setError("");
    try {
      await uploadDataset(file);
      navigate("/dashboard");
    } catch (requestError) {
      setError(apiErrorMessage(requestError));
      setProcessing(false);
    }
  }

  return (
    <div className={dark ? "app dark" : "app light"}>
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark"><span className="brand-ring">◎</span></div>
          <div className="brand-copy">
            <div className="brand-name">Project Vigilance</div>
            <div className="brand-subtitle">AML intelligence</div>
          </div>
        </div>
        <button
          type="button"
          aria-label="Change theme"
          className="theme-button"
          onClick={() => setDark((value) => !value)}
        >
          {dark ? <Sun size={20} /> : <Moon size={20} />}
        </button>
      </header>

      <main className="hero">
        <section className="hero-copy">
          <div className="eyebrow"><span className="status-dot" /> Financial crime investigation platform</div>
          <h1>Uncover money<br />laundering <span>with clarity.</span></h1>
          <p className="intro">
            Upload transactions, detect suspicious behaviour, score account risk,
            and follow the evidence from alert to report.
          </p>
          <FeatureList />
        </section>

        <div>
          {error ? <p role="alert" className="error-message">{error}</p> : null}
          {processing ? (
            <ProcessingCard file={selectedFile} />
          ) : (
            <UploadCard
              onProcess={handleStartProcessing}
              onContinue={() => navigate("/dashboard")}
            />
          )}
        </div>
      </main>
    </div>
  );
}
