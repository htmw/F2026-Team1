import Card from "../Card.jsx";
import ResultChip from "../ResultChip.jsx";
import TextLink from "../TextLink.jsx";
import TriageTile from "./TriageTile.jsx";
import { CONDITION_LABELS } from "../../data/labels.js";
import { formatDate } from "../../utils/format.js";
import "../../styles/patient/eye-summary-card.css";

const EYES = {
  right: { badge: "OD", title: "Right eye (OD)" },
  left: { badge: "OS", title: "Left eye (OS)" },
};

function EyeSummaryCard({ eye, screening }) {
  const { badge, title } = EYES[eye];

  return (
    <Card>
      <header className="eye-summary__header">
        <span className="eye-summary__badge mono-meta">{badge}</span>

        <div className="eye-summary__title">
          <h3 className="h3">{title}</h3>
          <p className="eye-summary__subtitle caption-rg">
            {screening
              ? `Latest screening ${formatDate(screening.created_at)} • ${screening.id}`
              : "No screening yet"}
          </p>
        </div>

        {screening?.overall_result && (
          <ResultChip result={screening.overall_result} />
        )}
      </header>

      {screening ? (
        <>
          <div className="eye-summary__tiles">
            {screening.conditions.map((item) => (
              <TriageTile
                key={item.condition}
                label={`${CONDITION_LABELS[item.condition]} triage`}
                score={
                  item.result === "uncertain" ? null : item.calibrated_score
                }
                result={item.result}
              />
            ))}
          </div>

          <footer className="eye-summary__footer">
            <TextLink
              to={`/results/${screening.id}/record`}
              trailingArrow
              strong
            >
              View full record
            </TextLink>
          </footer>
        </>
      ) : (
        <p className="eye-summary__empty body-rg">
          This eye has not been screened for this patient.
        </p>
      )}
    </Card>
  );
}

export default EyeSummaryCard;
