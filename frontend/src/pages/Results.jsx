import { useParams } from "react-router-dom";
import { ArrowLeft, ChevronRight } from "lucide-react";
import Banner from "../components/Banner.jsx";
import Button from "../components/Button.jsx";
import ConditionCard from "../components/ConditionCard.jsx";
import InfoNote from "../components/InfoNote.jsx";
import ResultChip from "../components/ResultChip.jsx";
import SummaryStrip from "../components/SummaryStrip.jsx";
import TextLink from "../components/TextLink.jsx";
import HeatmapPanel from "../components/results/HeatmapPanel.jsx";
import RiskSummary from "../components/results/RiskSummary.jsx";
import { useScreening } from "../hooks/useScreening.js";
import { assetUrl } from "../services/api.js";
import "../styles/results/results.css";
import { EYE_LABELS, CONDITION_LABELS } from "../data/labels.js";
import { formatDate } from "../utils/format.js";

const UNCERTAIN_MESSAGE =
  "Low image quality or the model is uncertain. Please refer for a full eye examination.";

function ResultsMessage({ children }) {
  return (
    <main className="main results">
      <div className="results__back">
        <TextLink to="/history">Back to History</TextLink>
      </div>
      <p className="body-md">{children}</p>
    </main>
  );
}

function Results() {
  const { id } = useParams();
  const { screening, error, isLoading } = useScreening(id);

  if (isLoading) return <ResultsMessage>Loading screening…</ResultsMessage>;

  if (error?.status === 404) {
    return <ResultsMessage>Screening {id} was not found.</ResultsMessage>;
  }

  if (error) {
    return (
      <ResultsMessage>
        Could not load screening {id}. {error.message}
      </ResultsMessage>
    );
  }

  if (screening.skipped) {
    return (
      <ResultsMessage>
        This eye was skipped, so there is no result to show.
      </ResultsMessage>
    );
  }

  const { patient, eye, image, model_version } = screening;
  const conditions = screening.conditions.map((item) => ({
    ...item,
    heatmap_url: assetUrl(item.heatmap_url),
  }));

  return (
    <main className="main results">
      <div className="results__back">
        <Button variant="secondary" icon={ArrowLeft} to="/upload">
          New screening
        </Button>
        <TextLink to="/history">or back to History</TextLink>
      </div>

      <Banner title="Triage, not diagnosis">
        This screening tool assists qualified practitioners in prioritizing
        clinical evaluations. It does not provide definitive diagnostic
        findings.
      </Banner>

      <SummaryStrip
        variant="panel"
        items={[
          {
            label: "Patient",
            value: (
              <TextLink to={`/patients/${patient.id.toLowerCase()}`} accent>
                {patient.full_name}, {patient.id}
              </TextLink>
            ),
          },
          { label: "Eye", value: EYE_LABELS[eye] },
          { label: "Date", value: formatDate(screening.created_at) },
          { label: "Screening ID", value: screening.id, tag: true },
        ]}
        asideLabel="Overall result:"
      >
        <ResultChip result={screening.overall_result} />
        <TextLink
          to={`/results/${screening.id}/record`}
          trailingIcon={ChevronRight}
          strong
        >
          View full record
        </TextLink>
      </SummaryStrip>

      <div className="results__layout">
        <HeatmapPanel photoUrl={assetUrl(image.url)} conditions={conditions} />

        <div className="results__conditions">
          {conditions.map((item) => (
            <ConditionCard
              key={item.condition}
              condition={CONDITION_LABELS[item.condition]}
              result={item.result}
            >
              {item.result === "uncertain" ? (
                <InfoNote variant="tile">{UNCERTAIN_MESSAGE}</InfoNote>
              ) : (
                <RiskSummary
                  score={item.calibrated_score}
                  threshold={item.threshold}
                  result={item.result}
                  isExample={model_version.is_mock}
                />
              )}
            </ConditionCard>
          ))}
        </div>
      </div>
    </main>
  );
}

export default Results;
