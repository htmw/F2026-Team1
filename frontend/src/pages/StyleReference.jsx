import { useState } from "react";
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
import Select from "../components/Select.jsx";
import FileDropzone from "../components/upload/FileDropzone.jsx";
import SummaryStrip from "../components/SummaryStrip.jsx";
import PageHeader from "../components/PageHeader.jsx";
import Alert from "../components/Alert.jsx";
import RadioCardGroup from "../components/RadioCardGroup.jsx";
import FundusPreview from "../components/upload/FundusPreview.jsx";
import ScreeningForm from "../components/upload/ScreeningForm.jsx";
import ResultChip from "../components/ResultChip.jsx";
import BackLink from "../components/BackLink.jsx";
import ConditionCard from "../components/ConditionCard.jsx";

function StyleReference() {
  const [patientId, setPatientId] = useState("");
  const [file, setFile] = useState(null);

  const [eye, setEye] = useState("OD");

  const [formPatient, setFormPatient] = useState("");
  const [formEye, setFormEye] = useState("OD");
  const [formFile, setFormFile] = useState(null);

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

      <div style={{ width: "48rem" }}>
        <Select
          placeholder="Select a patient"
          value={patientId}
          onChange={(e) => setPatientId(e.target.value)}
          options={[
            { value: "P-001", label: "P-001, Maria Lopez, 67" },
            { value: "P-002", label: "P-002, James Chen, 54" },
          ]}
        />
      </div>
      <div style={{ width: "60rem" }}>
        <FileDropzone file={file} onFile={setFile} />
      </div>

      <div style={{ width: "60rem" }}>
        <SummaryStrip />
      </div>

      <div style={{ width: "60rem" }}>
        <SummaryStrip
          patient="P-001, Maria Lopez, 67"
          eye="Right eye (OD)"
          fileName="maria_lopez_right_fundus.jpg"
        />
      </div>

      <PageHeader eyebrow="Clinical triage intake" title="New screening" />

      <PageHeader
        title="History"
        subtitle="Past screenings for your patients, most recent first"
      />

      <div style={{ width: "60rem" }}>
        <Alert
          title="Photo too dark to screen"
          actions={
            <>
              <Button variant="secondary">Retake photo</Button>
              <Button variant="secondary">Upload different photo</Button>
            </>
          }
        >
          The photo is almost completely black. Retake it, or upload another
          photo of the right eye.
        </Alert>
      </div>

      <div style={{ width: "60rem" }}>
        <Alert
          title="This file can't be opened as a photo"
          actions={<Button variant="secondary">Upload different photo</Button>}
        >
          The file may be damaged or not a JPG or PNG. Upload another photo of
          the right eye.
        </Alert>
      </div>

      <div style={{ width: "48rem" }}>
        <RadioCardGroup
          name="eye"
          value={eye}
          onChange={setEye}
          options={[
            { value: "OD", label: "Right eye (OD)" },
            { value: "OS", label: "Left eye (OS)" },
          ]}
        />
      </div>

      <div style={{ width: "48rem" }}>
        <FundusPreview src={file ? URL.createObjectURL(file) : null} />
      </div>

      <div style={{ width: "70rem" }}>
        <ScreeningForm
          patients={[
            { id: "P-001", name: "Maria Lopez", age: 67 },
            { id: "P-002", name: "James Chen", age: 54 },
          ]}
          patientId={formPatient}
          onPatientChange={setFormPatient}
          eye={formEye}
          onEyeChange={setFormEye}
          file={formFile}
          onFileChange={setFormFile}
          qualityReason={null}
          onReset={() => setFormFile(null)}
          canSubmit={Boolean(formPatient && formEye && formFile)}
          onSubmit={() => console.log("submit")}
        />
      </div>
      <div>
        <ResultChip result="no_concern" />
        <ResultChip result="refer" />
        <ResultChip result="uncertain" />
      </div>

      <div>
        <BackLink to="/history">Back to History</BackLink>
      </div>

      <div>
        <ConditionCard condition="Cataract" result="no_concern">
          <p className="body-rg">Risk score 0.14 (14%)</p>
        </ConditionCard>
        <ConditionCard condition="Glaucoma" result="refer">
          <p className="body-rg">Risk score 0.78 (78%)</p>
        </ConditionCard>
        <ConditionCard condition="Cataract" result="uncertain">
          <p className="body-rg">
            Low image quality or the model is uncertain.
          </p>
        </ConditionCard>
      </div>
    </main>
  );
}

export default StyleReference;
