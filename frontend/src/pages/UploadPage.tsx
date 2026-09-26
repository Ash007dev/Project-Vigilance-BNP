import { useState } from "react";
import { Moon, Sun } from "lucide-react";
import { useNavigate } from "react-router-dom";

import UploadCard from "../components/UploadCard";
import ProcessingCard from "../components/ProcessingCard";
import FeatureList from "../components/FeatureList";

import "../styles/app.css";


export default function UploadPage() {

  const navigate = useNavigate();

  const [dark, setDark] = useState(true);

  const [selectedFile, setSelectedFile] =
    useState<File | null>(null);

  const [processing, setProcessing] =
    useState(false);


  const handleStartProcessing = (
    file: File
  ) => {

    setSelectedFile(file);

    setProcessing(true);

  };


  const handleProcessingComplete = () => {

    /*
     * Automatically navigate to dashboard
     * after processing is complete.
     */

    navigate("/dashboard");

  };


  return (

    <div
      className={
        dark
          ? "app dark"
          : "app light"
      }
    >

      {/* HEADER */}

      <header className="topbar">

        <div className="brand">

          <div className="brand-mark">

            <span className="brand-ring">
              ◎
            </span>

          </div>


          <div className="brand-copy">

            <div className="brand-name">
              Argus
            </div>

            <div className="brand-subtitle">
              AML INTELLIGENCE
            </div>

          </div>

        </div>


        <button
          className="theme-button"
          onClick={() =>
            setDark((value) => !value)
          }
        >

          {dark ? (
            <Sun size={20} />
          ) : (
            <Moon size={20} />
          )}

        </button>

      </header>


      {/* MAIN */}

      <main className="hero">

        {/* LEFT */}

        <section className="hero-copy">

          <div className="eyebrow">

            <span className="status-dot" />

            Financial crime investigation platform

          </div>


          <h1>

            Uncover money

            <br />

            laundering{" "}

            <span>
              with clarity.
            </span>

          </h1>


          <p className="intro">

            Upload a transaction dataset and Argus
            screens every account for suspicious
            behaviour, scores risk, and gives
            investigators a clear, evidence-backed
            path from alert to report.

          </p>


          <FeatureList />

        </section>


        {/* RIGHT */}

        {processing ? (

          <ProcessingCard
            file={selectedFile}
            onComplete={
              handleProcessingComplete
            }
          />

        ) : (

          <UploadCard
            onProcess={
              handleStartProcessing
            }
          />

        )}

      </main>

    </div>

  );
}