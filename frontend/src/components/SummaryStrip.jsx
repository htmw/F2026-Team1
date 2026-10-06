import "../styles/summary-strip.css";

function SummaryStrip({ patient, eye, fileName }) {
  return (
    <dl className="summary-strip">
      <div className="summary-strip__item">
        <dt className="summary-strip__label label-mono">Patient</dt>
        <dd className="body-semibold">{patient || "—"}</dd>
      </div>

      <div className="summary-strip__item">
        <dt className="summary-strip__label label-mono">Eye</dt>
        <dd className="body-semibold">{eye || "—"}</dd>
      </div>

      <div className="summary-strip__item">
        <dt className="summary-strip__label label-mono">File name</dt>
        <dd
          className={`summary-strip__file mono-meta${
            fileName ? "" : " summary-strip__file--empty"
          }`}
        >
          {fileName || "No file selected"}
        </dd>
      </div>
    </dl>
  );
}

export default SummaryStrip;
