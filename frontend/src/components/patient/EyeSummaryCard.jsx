import { ChevronRight } from "lucide-react";
import Card from "../Card.jsx";
import ResultChip from "../ResultChip.jsx";
import TextLink from "../TextLink.jsx";
import AttentionPanel from "./AttentionPanel.jsx";
import TriageTile from "./TriageTile.jsx";
import { CONDITION_LABELS } from "../../data/labels.js";
import { assetUrl } from "../../services/api.js";
import { formatDate } from "../../utils/format.js";
import "../../styles/patient/eye-summary-card.css";

const EYES = {
  right: { badge: "OD", title: "Right eye (OD)" },
  left: { badge: "OS", title: "Left eye (OS)" },
};

function getAttention(screening) {
  const focus =
    screening.conditions.find((item) => item.result === "refer") ??
    screening.conditions.find((item) => item.result === "uncertain");

  if (focus) {
    return {
      imageUrl: assetUrl(focus.heatmap_url ?? screening.image?.url),
      eyebrow: "Model attention (Grad-CAM)",
      title: `${CONDITION_LABELS[focus.condition]} heatmap`,
      description: focus.flag_reason,
    };
  }

  return {
    imageUrl: assetUrl(screening.image?.url),
    eyebrow: "Original photo (color fundus)",
    title: "No referral findings",
    description:
      "Cataract and glaucoma are both below their referral thresholds.",
  };
}

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
                label={CONDITION_LABELS[item.condition]}
                score={
                  item.result === "uncertain" ? null : item.calibrated_score
                }
                result={item.result}
              />
            ))}
          </div>

          <AttentionPanel {...getAttention(screening)} />

          <footer className="eye-summary__footer">
            <TextLink
              to={`/results/${screening.id}/record`}
              trailingIcon={ChevronRight}
              strong
              accent
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
