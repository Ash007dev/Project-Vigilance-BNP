import {
  CheckCircle2,
  Circle,
} from "lucide-react";

import {
  useEffect,
  useState,
} from "react";


interface ProcessingCardProps {
  file: File | null;

  onComplete: () => void;
}


const stages = [

  "Uploading dataset...",

  "Validating data...",

  "Processing transactions...",

  "Analyzing suspicious activity...",

  "Generating risk scores...",

];


export default function ProcessingCard({
  file,
  onComplete,
}: ProcessingCardProps) {

  const [progress, setProgress] =
    useState(20);

  const [currentStage, setCurrentStage] =
    useState(1);


  useEffect(() => {

    const timer =
      window.setInterval(() => {

        setProgress((value) => {

          const next =
            Math.min(value + 20, 100);

          if (next === 100) {

            window.clearInterval(timer);

            /*
             * Give the user a tiny moment
             * to see 100%, then navigate.
             */

            window.setTimeout(() => {
              onComplete();
            }, 700);

          }

          return next;

        });


        setCurrentStage((stage) => {

          return Math.min(
            stage + 1,
            stages.length
          );

        });

      }, 1800);


    return () => {

      window.clearInterval(timer);

    };

  }, [onComplete]);


  const fileName =
    file?.name ||
    "Project_Vigilance_Dataset_Password_Protected.xlsx";


  return (

    <section className="processing-card">

      <div className="processing-heading">

        <h2>
          Analyzing your dataset
        </h2>

        <p>
          This usually takes a few moments.
        </p>

      </div>


      {/* FILE */}

      <div className="progress-meta">

        <strong>
          {fileName}
        </strong>

        <span>
          {progress}%
        </span>

      </div>


      {/* PROGRESS */}

      <div className="progress-track">

        <div
          className="progress-value"

          style={{
            width: `${progress}%`,
          }}
        />

      </div>


      {/* STEPS */}

      <div className="processing-steps">

        {stages.map(
          (label, index) => {

            const completed =
              index < currentStage;

            const active =
              index === currentStage;


            return (

              <div
                key={label}

                className={`
                  processing-step
                  ${
                    completed
                      ? "completed"
                      : active
                      ? "active"
                      : "pending"
                  }
                `}
              >

                <div className="step-icon">

                  {completed ? (

                    <CheckCircle2
                      size={19}
                    />

                  ) : (

                    <Circle
                      size={19}
                    />

                  )}

                </div>


                <span>
                  {label}
                </span>

              </div>

            );

          }
        )}

      </div>

    </section>

  );
}