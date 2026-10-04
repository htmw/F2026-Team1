import ThemeToggle from "../components/ThemeToggle.jsx";
import "../styles/global.css";
import { BarChart3, Download } from "lucide-react";
import Button from "../components/Button.jsx";

function StyleReference() {
  return (
    <div>
      <ThemeToggle />
      <button className="btn-primary" disabled>
        Disabled
      </button>

      <div className="chip chip--accent">tint accent</div>
      <div className="chip chip--success">tint accent</div>
      <div className="chip chip--danger">tint accent</div>
      <div className="chip chip--neutral">tint accent</div>

      <div className="tint-accent">Selected section</div>
      <div className="tint-success">Screening completed successfully</div>
      <div className="tint-danger">Image quality failed</div>

      <h1 className="h1">Heading 1</h1>
      <h2 className="h2">Heading 2</h2>
      <h3 className="h3">Heading 3</h3>

      <p className="body-rg">body regular</p>
      <p className="body-md">body medium</p>
      <p className="body-semibold">body semibold</p>
      <p className="caption-rg">caption regular</p>
      <p className="caption-md">caption medium</p>
      <p className="caption-semibold">caption semibold</p>
      <p className="label-micro">label micro</p>
      <p className="mono-score">mono score</p>
      <p className="mono-reference">mono reference</p>
      <p className="mono-meta">mono meta</p>
      <p className="logo-wordmark">logo wordmark</p>
      <p className="logo-descriptor">logo descriptor</p>

      <Button icon={BarChart3}>Screen this photo</Button>
      <Button variant="secondary" icon={Download}>
        Export Summary
      </Button>
      <Button icon={BarChart3} disabled>
        Screen this photo
      </Button>
      <Button icon={BarChart3} fullWidth>
        Full width
      </Button>
    </div>
  );
}

export default StyleReference;
