import { Info, AlertTriangle } from "lucide-react";
import Card from "../components/Card.jsx";
import Chip from "../components/Chip.jsx";
import PageHeader from "../components/PageHeader.jsx";
import "../styles/about/about.css";

const DATASETS = [
  "ODIR-5K",
  "ORIGA",
  "DRISHTI-GS",
  "ACRIMA",
  "retina_dataset_2016",
];

function About() {
  return (
    <main className="main">
      <PageHeader
        eyebrow={
          <>
            System reference /{" "}
            <span className="about__crumb">Documentation</span>
          </>
        }
        title="About"
      />

      <div className="about__grid">
        <div className="about__column">
          <Card
            className="about__card"
            title="01 / What DUAL is"
            aside={
              <Chip tone="neutral" icon={Info}>
                Triage, not diagnosis
              </Chip>
            }
          >
            <p className="about__text">
              A student research prototype that flags possible cataract and
              glaucoma from one fundus photograph of one eye, so the eye can be
              referred for a full examination. It is triage, not diagnosis. It
              is not a medical device and is not FDA cleared. Non-commercial
              academic project, Pace University CS691, team EyeQ.
            </p>
          </Card>

          <Card className="about__card" title="02 / How it works">
            <p className="about__text">
              One shared ResNet backbone with two heads: cataract vs not, and
              glaucoma vs not. Scores are calibrated on ODIR-5K validation data.
              When the photo is poor or the model is unsure, it answers
              Uncertain, refer.
            </p>
          </Card>

          <Card className="about__card" title="03 / Training and testing">
            <p className="about__text">
              Trained only on ODIR-5K. Tested on photos it never saw: glaucoma
              on ORIGA, DRISHTI-GS and ACRIMA; cataract and glaucoma on
              retina_dataset_2016. Results: pending.
            </p>
          </Card>

          <section className="about__limits">
            <h2 className="about__limits-title label-mono">
              <AlertTriangle size={16} aria-hidden="true" />
              Known limits
            </h2>
            <p className="about__text">
              Cataract testing on outside data relies on a single dataset
              (retina_dataset_2016) whose origin is not documented, so cataract
              results are less certain than glaucoma results. The model may
              confuse a hazy or blurry photo with cataract. Heatmaps show what
              influenced a score, not proof of disease. Calibration may be
              weaker on photos from other cameras.
            </p>
          </section>
        </div>

        <div className="about__column">
          <Card className="about__card" title="04 / Model version">
            <p className="about__version mono-score">v1.0 (demo)</p>
          </Card>

          <Card className="about__card" title="05 / Dataset credits">
            <ul className="about__datasets">
              {DATASETS.map((name) => (
                <li key={name} className="about__dataset">
                  <span className="mono-reference">{name}</span>
                  <span className="mono-meta">[citation]</span>
                </li>
              ))}
            </ul>
          </Card>
        </div>
      </div>
    </main>
  );
}

export default About;
