import { useParams } from "react-router-dom";
import { CheckCircle2, AlertTriangle, Printer, HelpCircle } from "lucide-react";
import Button from "../components/Button.jsx";
import Card from "../components/Card.jsx";
import Chip from "../components/Chip.jsx";
import ConditionCard from "../components/ConditionCard.jsx";
import InfoNote from "../components/InfoNote.jsx";
import PageHeader from "../components/PageHeader.jsx";
import TextLink from "../components/TextLink.jsx";
import ConditionDetail from "../components/record/ConditionDetail.jsx";
import HeatmapTile from "../components/record/HeatmapTile.jsx";
import { useScreening } from "../hooks/useScreening.js";
import { assetUrl } from "../services/api.js";
import "../styles/record/record.css";
import { EYE_LABELS, CONDITION_LABELS, RESULT_LABELS } from "../data/labels.js";
import { formatDateTime } from "../utils/format.js";

const INFLUENCE = {
  no_concern: "Low influence intensity",
  refer: "Elevated influence pattern",
  uncertain: "Influence unclear",
};

function RecordMessage({ children }) {
  return (
    <main className="main record">
      <div>
        <TextLink to="/history">Back to History</TextLink>
      </div>
      <p className="body-md">{children}</p>
    </main>
  );
}

function Record() {
  const { id } = useParams();
  const { screening, error, isLoading } = useScreening(id);

  if (isLoading)
    return <RecordMessage>Loading screening record…</RecordMessage>;

  if (error?.status === 404) {
    return <RecordMessage>Screening {id} was not found.</RecordMessage>;
  }

  if (error) {
    return (
      <RecordMessage>
        Could not load screening {id}. {error.message}
      </RecordMessage>
    );
  }

  if (screening.skipped) {
    return (
      <RecordMessage>
        This eye was skipped, so there is no record to show.
      </RecordMessage>
    );
  }

  const { patient, eye, image, model_version, conditions } = screening;
  const qualityPassed = image.quality_status === "passed";

  return (
    <main className="main record">
      <div>
        <TextLink to="/history">Back to History</TextLink>
      </div>

      <PageHeader
        title="Screening record"
        subtitle={
          <span className="record__meta">
            <span className="record__id mono-meta">{screening.id}</span>
            <span>{formatDateTime(screening.created_at)}</span>
            <span>
              Patient:{" "}
              <TextLink to={`/patients/${patient.id.toLowerCase()}`} accent>
                {patient.full_name}, {patient.id}
              </TextLink>
            </span>
            <span>Eye: {EYE_LABELS[eye]}</span>
            <span>Model version: {model_version.id}</span>
          </span>
        }
        actions={
          <Button
            variant="secondary"
            icon={Printer}
            href={assetUrl(`/screenings/${screening.id}/export`)}
          >
            Export summary
          </Button>
        }
      />

      <div className="record__quality">
        {qualityPassed ? (
          <CheckCircle2 size={20} aria-hidden />
        ) : (
          <AlertTriangle size={20} aria-hidden />
        )}
        <span className="body-semibold">Image quality check:</span>
        <Chip tone={qualityPassed ? "success" : "danger"} mono>
          {qualityPassed ? "Passed" : "Failed"}
        </Chip>
      </div>

      <div className="record__conditions">
        {conditions.map((item) => (
          <ConditionCard
            key={item.condition}
            eyebrow="Condition"
            condition={CONDITION_LABELS[item.condition]}
            result={item.result}
          >
            <ConditionDetail item={item} isExample={model_version.is_mock} />
          </ConditionCard>
        ))}
      </div>

      <InfoNote icon={HelpCircle}>
        Status variant definition: Uncertain means low image quality or the
        model is uncertain.
      </InfoNote>

      <Card title="Model influence heatmaps">
        <p className="record__section-hint body-rg">
          Shows what influenced each score, not where disease is.
        </p>
        <div className="record__heatmaps">
          {conditions.map((item) => (
            <HeatmapTile
              key={item.condition}
              title={`${CONDITION_LABELS[item.condition]} heatmap`}
              description={INFLUENCE[item.result]}
              result={item.result}
              resultLabel={RESULT_LABELS[item.result]}
              imageUrl={assetUrl(item.heatmap_url)}
            />
          ))}
        </div>
      </Card>
    </main>
  );
}

export default Record;
