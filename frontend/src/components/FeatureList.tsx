import {
  Network,
  ScanSearch,
  Gauge,
} from "lucide-react";

const features = [
  {
    icon: ScanSearch,
    title: "Pattern detection",
    text: "Structuring, layering, mule networks and crypto off-ramping.",
  },
  {
    icon: Gauge,
    title: "Explainable risk scores",
    text: "Every flag comes with the evidence behind it.",
  },
  {
    icon: Network,
    title: "Money-flow graphs",
    text: "Trace funds across accounts, devices and wallets.",
  },
];

export default function FeatureList() {

  return (

    <div className="feature-list">

      {features.map(
        ({ icon: Icon, title, text }) => (

          <div
            className="feature"
            key={title}
          >

            <div className="feature-icon">

              <Icon
                size={20}
                strokeWidth={1.7}
              />

            </div>


            <div>

              <div className="feature-title">
                {title}
              </div>

              <div className="feature-text">
                {text}
              </div>

            </div>

          </div>

        )
      )}

    </div>

  );
}