export const SCREENING_COLUMNS = [
  { key: "created_at", label: "Date", width: "1.2fr", type: "date" },
  { key: "id", label: "Screening ID", width: "1.1fr", type: "link" },
  {
    key: "patient_name",
    label: "Patient",
    width: "1.8fr",
    type: "person",
    idKey: "patient_id",
  },
  {
    key: "eye",
    label: "Eye",
    width: "1.5fr",
    type: "chip",
    labels: { right: "Right eye (OD)", left: "Left eye (OS)" },
  },
  { key: "overall_result", label: "Overall", width: "1.4fr", type: "result" },
  { key: "cataract", label: "Cataract", width: "1.6fr", type: "result" },
  { key: "glaucoma", label: "Glaucoma", width: "1.4fr", type: "result" },
  {
    key: "open",
    label: "Open record",
    width: "3.2rem",
    type: "chevron",
    align: "end",
    hidden: true,
  },
];

export const PATIENT_SCREENING_COLUMNS = [
  { key: "created_at", label: "Date", width: "1.6fr", type: "datetime" },
  { key: "id", label: "Screening ID", width: "1.1fr", type: "link" },
  {
    key: "eye",
    label: "Eye tested",
    width: "1.5fr",
    type: "chip",
    labels: { right: "OD • Right eye", left: "OS • Left eye" },
  },
  { key: "overall_result", label: "Overall triage", width: "1.4fr", type: "result" },
  { key: "cataract", label: "Cataract", width: "1.6fr", type: "result" },
  { key: "glaucoma", label: "Glaucoma", width: "1.4fr", type: "result" },
  {
    key: "open",
    label: "Open record",
    width: "3.2rem",
    type: "chevron",
    align: "end",
    hidden: true,
  },
];