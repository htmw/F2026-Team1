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
  ShieldCheck,
  ArrowLeft,
  Plus,
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
import ConditionCard from "../components/ConditionCard.jsx";
import MetaList from "../components/MetaList.jsx";
import Table from "../components/Table";
import { SCREENING_COLUMNS } from "../data/screeningColumns.js";
import { SCREENINGS } from "../data/screenings.js";
import RiskRing from "../components/RiskRing.jsx";
import SegmentedControl from "../components/SegmentedControl.jsx";
import HeatmapPanel from "../components/results/HeatmapPanel.jsx";
import cataractHeatmap from "../assets/images/cataractHeatmap.png";
import glaucomaHeatmap from "../assets/images/glaucomaHeatmap.png";
import eyePhoto from "../assets/images/eye.png";
import RiskSummary from "../components/results/RiskSummary.jsx";
import Banner from "../components/Banner.jsx";
import TextLink from "../components/TextLink.jsx";
import Meter from "../components/Meter.jsx";
import HeatmapTile from "../components/record/HeatmapTile.jsx";
import ConditionDetail from "../components/record/ConditionDetail.jsx";
import TriageTile from "../components/patient/TriageTile.jsx";
import EyeSummaryCard from "../components/patient/EyeSummaryCard.jsx";
import PatientHeader from "../components/patient/PatientHeader.jsx";

function StyleReference() {
  const [patientId, setPatientId] = useState("");
  const [file, setFile] = useState(null);

  const [eye, setEye] = useState("OD");

  const [formPatient, setFormPatient] = useState("");
  const [formEye, setFormEye] = useState("OD");
  const [formFile, setFormFile] = useState(null);

  const [condition, setCondition] = useState("glaucoma");

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

      <Button variant="secondary" icon={ArrowLeft} to="/upload">
        New screening
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

      <InfoNote icon={ShieldCheck} title="Triage, not diagnosis">
        This screening tool assists qualified practitioners in prioritizing
        clinical evaluations. It does not provide definitive diagnostic
        findings.
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
        <SummaryStrip
          items={[
            { label: "Patient", value: "—" },
            { label: "Eye", value: "—" },
            { label: "File name", value: "No file selected", mono: true },
          ]}
        />
      </div>

      <div style={{ width: "60rem" }}>
        <SummaryStrip
          items={[
            { label: "Patient", value: "P-001, Maria Lopez, 67" },
            { label: "Eye", value: "Right eye (OD)" },
            {
              label: "File name",
              value: "maria_lopez_right_fundus.jpg",
              mono: true,
            },
          ]}
        />
      </div>

      <div style={{ width: "128rem" }}>
        <SummaryStrip
          items={[
            { label: "Patient", value: "Maria Lopez, P-001" },
            { label: "Eye", value: "Right eye, OD" },
            { label: "Date", value: "Oct 9, 2026" },
            { label: "Screening ID", value: "SCR-0008", mono: true },
          ]}
          asideLabel="Overall result:"
        >
          <ResultChip result="refer" />
        </SummaryStrip>
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

      <div>
        <MetaList
          items={[
            { label: "Patient", value: "Maria Lopez, P-001" },
            { label: "Eye", value: "Right eye, OD" },
            { label: "Date", value: "Sep 22, 2026" },
            { label: "Screening ID", value: "#SCR-2026-8841", mono: true },
          ]}
        />
      </div>

      <div>
        <Table
          label="Past screenings"
          columns={SCREENING_COLUMNS}
          rows={SCREENINGS}
          rowHref={(row) => `/results/${row.id}`}
        />
      </div>

      <div style={{ display: "flex", gap: "2.4rem" }}>
        <RiskRing value={0.14} result="no_concern" />
        <RiskRing value={0.78} result="refer" />
        <RiskRing value={0.5} result="uncertain" />
        <RiskRing value={0} result="no_concern" />
        <RiskRing value={1} result="refer" />
      </div>

      <div>
        <SegmentedControl
          label="Heatmap condition"
          options={[
            { value: "cataract", label: "Cataract" },
            { value: "glaucoma", label: "Glaucoma" },
          ]}
          value={condition}
          onChange={setCondition}
        />
      </div>

      <div style={{ width: "70rem" }}>
        <HeatmapPanel
          photoUrl={eyePhoto}
          conditions={[
            { condition: "cataract", heatmap_url: null },
            { condition: "glaucoma", heatmap_url: null },
          ]}
        />

        <HeatmapPanel
          photoUrl={eyePhoto}
          conditions={[
            { condition: "cataract", heatmap_url: cataractHeatmap },
            { condition: "glaucoma", heatmap_url: glaucomaHeatmap },
          ]}
        />
      </div>

      <div>
        <ConditionCard condition="Cataract" result="no_concern">
          <RiskSummary
            score={0.14}
            threshold={0.35}
            result="no_concern"
            isExample
          />
        </ConditionCard>
        <ConditionCard condition="Glaucoma" result="refer">
          <RiskSummary score={0.78} threshold={0.5} result="refer" isExample />
        </ConditionCard>
      </div>

      <div>
        <Banner title="Triage, not diagnosis">
          This screening tool assists qualified practitioners in prioritizing
          clinical evaluations. It does not provide definitive diagnostic
          findings.
        </Banner>
      </div>

      <div>
        <TextLink to="/history" leadingArrow>
          Back to History
        </TextLink>
        <TextLink to="/history">or back to History</TextLink>
      </div>

      <div>
        <h1>Meter Component</h1>
        <Meter value={0.14} result="no_concern" label="Calibrated risk" />
        <Meter value={0.78} result="refer" label="Calibrated risk" />
        <Meter value={0.5} result="uncertain" label="Calibrated risk" />
        <Meter
          value={0.14}
          marker={0.35}
          result="no_concern"
          label="Calibrated risk against threshold"
        />
        <Meter
          value={0.78}
          marker={0.5}
          result="refer"
          label="Calibrated risk against threshold"
        />
      </div>

      <div>
        <HeatmapTile
          title="Cataract heatmap"
          description="Low influence intensity"
          result="no_concern"
          resultLabel="No concern"
          imageUrl={cataractHeatmap}
        />
        <HeatmapTile
          title="Glaucoma heatmap"
          description="Elevated influence pattern"
          result="refer"
          resultLabel="Refer"
          imageUrl={glaucomaHeatmap}
        />
        <HeatmapTile
          title="Cataract heatmap"
          description="Influence unclear"
          result="uncertain"
          resultLabel="Uncertain, refer"
          imageUrl={eyePhoto}
        />
      </div>

      <div>
        <ConditionCard
          condition="Cataract"
          eyebrow="Condition"
          result="no_concern"
        >
          <ConditionDetail
            isExample
            item={{
              calibrated_score: 0.14,
              raw_score: 0.12,
              threshold: 0.35,
              result: "no_concern",
              flag_reason:
                "Calibrated risk 0.14 is below the referral threshold 0.35.",
            }}
          />
        </ConditionCard>
        <ConditionCard condition="Glaucoma" eyebrow="Condition" result="refer">
          <ConditionDetail
            isExample
            item={{
              calibrated_score: 0.78,
              raw_score: 0.81,
              threshold: 0.5,
              result: "refer",
              flag_reason:
                "Calibrated risk 0.78 is at or above the referral threshold 0.50.",
            }}
          />
        </ConditionCard>
        <ConditionCard
          condition="Cataract"
          eyebrow="Condition"
          result="uncertain"
        >
          <ConditionDetail
            item={{
              calibrated_score: 0.5,
              raw_score: 0.5,
              threshold: 0.35,
              result: "uncertain",
              flag_reason:
                "Low image quality or the model is uncertain. Please refer for a full eye examination.",
            }}
          />
        </ConditionCard>
      </div>
      <div>
        <TriageTile label="Cataract triage" score={0.14} result="no_concern" />
        <TriageTile label="Glaucoma triage" score={0.78} result="refer" />
        <TriageTile label="Cataract triage" score={0.5} result="uncertain" />
        <TriageTile label="Glaucoma triage" />
      </div>
      <div>
        <EyeSummaryCard
          eye="right"
          screening={{
            id: "SCR-0841",
            created_at: "2026-09-22T18:15:00Z",
            overall_result: "refer",
            conditions: [
              {
                condition: "cataract",
                calibrated_score: 0.14,
                result: "no_concern",
              },
              {
                condition: "glaucoma",
                calibrated_score: 0.78,
                result: "refer",
              },
            ],
          }}
        />
        <EyeSummaryCard eye="left" screening={null} />
      </div>
      <div>
        <PatientHeader
          patient={{
            id: "P-001",
            full_name: "Maria Lopez",
            age: 67,
            sex: "female",
          }}
          lastEncounter="Sep 22, 2026"
          protocolComplete
          actions={
            <>
              <Button variant="secondary" icon={Download}>
                Export Dossier
              </Button>
              <Button icon={Plus} to="/upload">
                New screening
              </Button>
            </>
          }
        />
      </div>
    </main>
  );
}

export default StyleReference;
