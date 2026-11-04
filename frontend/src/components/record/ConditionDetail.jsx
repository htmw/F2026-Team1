import InfoNote from "../InfoNote.jsx";
import Meter from "../Meter.jsx";
import "../../styles/record/condition-detail.css";

function ConditionDetail({ item, isExample = false }) {
  const { calibrated_score, raw_score, threshold, result, flag_reason } = item;

  if (result === "uncertain") {
    return <InfoNote title="Why it was flagged">{flag_reason}</InfoNote>;
  }

  const points = Math.round(Math.abs(calibrated_score - threshold) * 100);
  const direction = calibrated_score >= threshold ? "above" : "below";

  return (
    <div className="condition-detail">
      <div className="condition-detail__stats">
        <div className="condition-detail__tile">
          <p className="label-mono condition-detail__label">Calibrated risk</p>
          <p
            className={`condition-detail__value condition-detail__value--${result}`}
          >
            {calibrated_score.toFixed(2)}
          </p>
          <Meter
            value={calibrated_score}
            result={result}
            label="Calibrated risk"
          />
        </div>

        <div className="condition-detail__tile">
          <p className="label-mono condition-detail__label">Raw score</p>
          <p className="condition-detail__value">{raw_score.toFixed(2)}</p>
          <p className="condition-detail__threshold">
            <span className="label-mono">Threshold</span>
            <span className="mono-meta">
              {threshold.toFixed(2)}
              {isExample && " (example)"}
            </span>
          </p>
        </div>
      </div>

      <div className="condition-detail__tile">
        <p className="condition-detail__difference">
          <span className="label-mono condition-detail__label">Difference</span>
          <span
            className={`mono-meta condition-detail__points condition-detail__points--${result}`}
          >
            {points} points {direction} threshold
          </span>
        </p>
        <Meter
          value={calibrated_score}
          marker={threshold}
          result={result}
          label="Calibrated risk against threshold"
        />
      </div>

      <InfoNote title="Why it was flagged">{flag_reason}</InfoNote>
    </div>
  );
}

export default ConditionDetail;
