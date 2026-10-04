import ThemeToggle from "../components/ThemeToggle.jsx";
import "../styles/global.css";
import {
  BarChart3,
  Download,
  Check,
  HelpCircle,
  AlertTriangle,
  CheckCircle2,
} from "lucide-react";
import Button from "../components/Button.jsx";
import Chip from "../components/Chip.jsx";
import InfoNote from "../components/InfoNote.jsx";
import Card from "../components/Card.jsx";

function StyleReference() {
  return (
    <main className="style-main">
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

      <Chip mono>Demo data</Chip>
      <Chip mono>JPG OR PNG</Chip>
      <Chip tone="success" icon={Check} mono>
        maria_lopez_right_fundus.jpg
      </Chip>
      <Chip tone="success" icon={CheckCircle2}>
        No concern
      </Chip>
      <Chip tone="danger" icon={AlertTriangle}>
        Refer
      </Chip>
      <Chip tone="warning" icon={HelpCircle}>
        Uncertain, refer
      </Chip>

      <InfoNote>
        DUAL flags eyes that may need a specialist review for cataract or
        glaucoma. It does not diagnose. Every Refer or Uncertain result needs a
        full eye examination.
      </InfoNote>

      <Card title="Fundus preview" aside="Awaiting capture">
        <p className="body-rg">Card content goes here</p>
      </Card>

      <Card>
        <p className="body-rg">A card with no header</p>
      </Card>
    </main>
  );
}

export default StyleReference;
