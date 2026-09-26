import { CheckCircle2, Circle } from "lucide-react";
import { useEffect, useState } from "react";


type ProcessingCardProps = {
  file: File | null;
};

const stages = [
  "Uploading dataset",
  "Validating and cleaning rows",
  "Saving transactions",
  "Preparing detection data",
];

export default function ProcessingCard({ file }: ProcessingCardProps) {
  const [currentStage, setCurrentStage] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setCurrentStage((stage) => Math.min(stage + 1, stages.length - 1));
    }, 1600);
    return () => window.clearInterval(timer);
  }, []);

  const progress = Math.min(20 + currentStage * 22, 88);

  return (
    <section className="processing-card" aria-live="polite">
      <div className="processing-heading">
        <h2>Processing your dataset</h2>
        <p>The dashboard will open when the API finishes.</p>
      </div>

      <div className="progress-meta">
        <strong>{file?.name ?? "Transaction dataset"}</strong>
        <span>{progress}%</span>
      </div>

      <div className="progress-track">
        <div className="progress-value" style={{ width: `${progress}%` }} />
      </div>

      <div className="processing-steps">
        {stages.map((label, index) => {
          const completed = index < currentStage;
          const active = index === currentStage;
          return (
            <div
              key={label}
              className={`processing-step ${completed ? "completed" : active ? "active" : "pending"}`}
            >
              <div className="step-icon">
                {completed ? <CheckCircle2 size={19} /> : <Circle size={19} />}
              </div>
              <span>{label}</span>
            </div>
          );
        })}
      </div>
    </section>
  );
}
