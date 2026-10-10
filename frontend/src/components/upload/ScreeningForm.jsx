import { BarChart3 } from "lucide-react";
import Alert from "../Alert.jsx";
import Button from "../Button.jsx";
import Card from "../Card.jsx";
import Chip from "../Chip.jsx";
import FileDropzone from "./FileDropzone.jsx";
import RadioCardGroup from "../RadioCardGroup.jsx";
import Select from "../Select.jsx";
import SummaryStrip from "../SummaryStrip.jsx";
import "../../styles/upload/screening-form.css";

const EYE_OPTIONS = [
  { value: "OD", label: "Right eye (OD)" },
  { value: "OS", label: "Left eye (OS)" },
];

const ALERTS = {
  too_dark: {
    title: "Photo too dark to screen",
    text: (eye) =>
      `The photo is almost completely black. Retake it, or upload another photo of the ${eye} eye.`,
    canRetake: true,
  },
  not_fundus: {
    title: "This doesn't look like a fundus photo",
    text: (eye) =>
      `Upload a full fundus photo of the ${eye} eye, straight from the camera.`,
    canRetake: true,
  },
  unreadable: {
    title: "This file can't be opened as a photo",
    text: (eye) =>
      `The file may be damaged or not a JPG or PNG. Upload another photo of the ${eye} eye.`,
    canRetake: false,
  },
};

function ScreeningForm({
  patients,
  patientId,
  onPatientChange,
  eye,
  onEyeChange,
  file,
  onFileChange,
  qualityReason,
  onReset,
  canSubmit,
  onSubmit,
}) {
  const patient = patients.find((p) => p.id === patientId);
  const patientLabel =
    patient && `${patient.id}, ${patient.name}, ${patient.age}`;
  const eyeLabel = EYE_OPTIONS.find((option) => option.value === eye)?.label;
  const alert = ALERTS[qualityReason];
  const eyeWord = eye === "OD" ? "right" : "left";

  function handleSubmit(e) {
    e.preventDefault();
    if (canSubmit) onSubmit();
  }

  return (
    <Card>
      <h2 className="h2 screening-form__title">Screening Configuration</h2>

      <form className="screening-form" onSubmit={handleSubmit}>
        <div className="screening-form__step">
          <div className="screening-form__step-head">
            <h3 id="step-patient" className="label-mono">
              Step 1: Select patient
            </h3>
            <Chip mono>Demo data</Chip>
          </div>
          <Select
            aria-labelledby="step-patient"
            placeholder="Select a patient"
            value={patientId}
            onChange={(e) => onPatientChange(e.target.value)}
            options={patients.map((p) => ({
              value: p.id,
              label: `${p.id}, ${p.name}, ${p.age}`,
            }))}
          />
        </div>

        <div className="screening-form__step">
          <h3 id="step-eye" className="label-mono">
            Step 2: Which eye
          </h3>
          <RadioCardGroup
            aria-labelledby="step-eye"
            name="eye"
            options={EYE_OPTIONS}
            value={eye}
            onChange={onEyeChange}
          />
          <p className="caption-rg screening-form__hint">
            Screen each eye separately.
          </p>
        </div>

        <div className="screening-form__step">
          <h3 id="step-photo" className="label-mono">
            {file
              ? "Step 3: Upload fundus photo (JPG or PNG)"
              : "Step 3: Fundus photo"}
          </h3>
          <FileDropzone file={file} onFile={onFileChange} />

          {alert && (
            <Alert
              title={alert.title}
              actions={
                <>
                  {alert.canRetake && (
                    <Button variant="secondary" onClick={onReset}>
                      Retake photo
                    </Button>
                  )}
                  <Button variant="secondary" onClick={onReset}>
                    Upload different photo
                  </Button>
                </>
              }
            >
              {alert.text(eyeWord)}
            </Alert>
          )}
        </div>

        <SummaryStrip
          patient={patientLabel}
          eye={eyeLabel}
          fileName={file?.name}
        />

        <Button type="submit" icon={BarChart3} fullWidth disabled={!canSubmit}>
          Screen this photo
        </Button>
      </form>
    </Card>
  );
}

export default ScreeningForm;
