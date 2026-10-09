import { useState } from "react";
import FundusPreview from "../components/FundusPreview.jsx";
import InfoNote from "../components/InfoNote.jsx";
import PageHeader from "../components/PageHeader.jsx";
import ScreeningForm from "../components/ScreeningForm.jsx";
import "../styles/upload.css";

const PATIENTS = [
  { id: "P-001", name: "Maria Lopez", age: 67 },
  { id: "P-002", name: "James Chen", age: 54 },
  { id: "P-003", name: "Aisha Patel", age: 61 },
  { id: "P-004", name: "David Brown", age: 72 },
];

function Upload() {
  const [patientId, setPatientId] = useState("P-001");
  const [eye, setEye] = useState("OD");
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [qualityReason, setQualityReason] = useState(null);

  const canSubmit = Boolean(patientId && file && !qualityReason);

  function handleFileChange(newFile) {
    if (previewUrl) URL.revokeObjectURL(previewUrl);

    setFile(newFile);
    setPreviewUrl(newFile ? URL.createObjectURL(newFile) : null);
  }

  function handleReset() {
    handleFileChange(null);
    setQualityReason(null);
  }

  function handleSubmit() {
    console.log("screen", { patientId, eye, file });
  }

  return (
    <main className="main">
      <PageHeader eyebrow="Clinical triage intake" title="New screening" />

      <div className="upload__grid">
        <div className="upload__left">
          <FundusPreview src={previewUrl} />
          <InfoNote>
            DUAL flags eyes that may need a specialist review for cataract or
            glaucoma. It does not diagnose. Every Refer or Uncertain result
            needs a full eye examination.
          </InfoNote>
        </div>

        <ScreeningForm
          patients={PATIENTS}
          patientId={patientId}
          onPatientChange={setPatientId}
          eye={eye}
          onEyeChange={setEye}
          file={file}
          onFileChange={handleFileChange}
          qualityReason={qualityReason}
          onReset={handleReset}
          canSubmit={canSubmit}
          onSubmit={handleSubmit}
        />
      </div>
    </main>
  );
}

export default Upload;
