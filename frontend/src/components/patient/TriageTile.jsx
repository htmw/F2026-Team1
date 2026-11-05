import Meter from "../Meter.jsx";
import ResultChip from "../ResultChip.jsx";
import "../../styles/patient/triage-tile.css";

function TriageTile({ label, score, result }) {
  const hasScore = score !== null && score !== undefined;

  return (
    <div className="triage-tile">
      <p className="triage-tile__label label-mono">{label}</p>

      <div className="triage-tile__row">
        <p className="mono-score">{hasScore ? score.toFixed(2) : "—"}</p>
        {result && <ResultChip result={result} />}
      </div>

      {hasScore && result && (
        <Meter value={score} result={result} label={label} />
      )}
    </div>
  );
}

export default TriageTile;
