import { History as HistoryIcon, ScanEye } from "lucide-react";
import Banner from "../components/Banner.jsx";
import Button from "../components/Button.jsx";
import Card from "../components/Card.jsx";
import ResultChip from "../components/ResultChip.jsx";
import heroImage from "../assets/images/eye.png";
import heroRing from "../assets/images/heroRing.png";
import "../styles/home/home.css";

const STEPS = [
  {
    title: "Choose the patient and eye",
    text: "Each eye is screened on its own, with its own photo.",
  },
  {
    title: "Upload a fundus photo",
    text: "DUAL checks the photo quality first. A photo that is too dark, or is not a fundus image, is rejected so you can retake it.",
  },
  {
    title: "Review the result",
    text: "You get a result for cataract and glaucoma, each with a risk score and a heatmap.",
  },
];

const RESULTS = [
  {
    result: "no_concern",
    text: "Both scores are below their referral thresholds.",
  },
  {
    result: "refer",
    text: "At least one condition is at or above its threshold.",
  },
  {
    result: "uncertain",
    text: "The photo or the model is too uncertain to call.",
  },
];

function Home() {
  return (
    <main className="main home">
      <section className="home__hero">
        <div className="home__hero-copy">
          <h1 className="home__title">Two conditions. One photograph.</h1>
          <p className="home__lead">
            DUAL reads a single fundus photo and flags eyes that may need a full
            examination for cataract or glaucoma.
          </p>

          <div className="home__actions">
            <Button icon={ScanEye} to="/upload">
              Start a screening
            </Button>
            <Button variant="secondary" icon={HistoryIcon} to="/history">
              View history
            </Button>
          </div>
        </div>

        <div className="home__hero-visual">
          <img className="home__hero-ring" src={heroRing} alt="" />
          <img
            className="home__hero-image"
            src={heroImage}
            alt="Fundus photograph of a retina"
          />
          <div className="home__hero-fade" aria-hidden="true" />
        </div>
      </section>

      <Banner title="Triage, not diagnosis">
        This screening tool assists qualified practitioners in prioritizing
        clinical evaluations. It does not provide definitive diagnostic
        findings.
      </Banner>

      <section className="home__section">
        <h2 className="h2">How a screening works</h2>
        <ol className="home__steps">
          {STEPS.map((step, index) => (
            <li key={step.title}>
              <Card>
                <p className="home__step label-mono">Step {index + 1}</p>
                <h3 className="h3">{step.title}</h3>
                <p className="home__text body-rg">{step.text}</p>
              </Card>
            </li>
          ))}
        </ol>
      </section>

      <section className="home__section">
        <Card>
          <h2 className="h2">Reading a result</h2>
          <p className="home__text body-rg">
            Each eye gets one of three results. Refer and Uncertain both mean
            the eye needs a full examination.
          </p>
          <ul className="home__results">
            {RESULTS.map((item) => (
              <li key={item.result} className="home__result">
                <ResultChip result={item.result} />
                <p className="body-rg">{item.text}</p>
              </li>
            ))}
          </ul>
        </Card>
      </section>
    </main>
  );
}

export default Home;
