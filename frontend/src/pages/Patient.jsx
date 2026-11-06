import { useParams } from "react-router-dom";
import { Download, Plus } from "lucide-react";
import Button from "../components/Button.jsx";
import Chip from "../components/Chip.jsx";
import InfoNote from "../components/InfoNote.jsx";
import Table from "../components/Table.jsx";
import TextLink from "../components/TextLink.jsx";
import EyeSummaryCard from "../components/patient/EyeSummaryCard.jsx";
import PatientHeader from "../components/patient/PatientHeader.jsx";
import { PATIENT_SCREENING_COLUMNS } from "../data/screeningColumns.js";
import { useApi } from "../hooks/useApi.js";
import { assetUrl } from "../services/api.js";
import { formatDate } from "../utils/format.js";
import "../styles/patient/patient.css";

function PatientMessage({ children }) {
  return (
    <main className="main patient">
      <div>
        <TextLink to="/history">Back to history</TextLink>
      </div>
      <p className="body-md">{children}</p>
    </main>
  );
}

function Patient() {
  const { id: rawId } = useParams();
  const id = rawId?.toUpperCase();

  const {
    data: detail,
    error,
    isLoading,
  } = useApi(`/patients/${encodeURIComponent(id)}`);
  const { data: screenings } = useApi(
    `/patients/${encodeURIComponent(id)}/screenings`,
  );

  if (isLoading) return <PatientMessage>Loading patient…</PatientMessage>;

  if (error?.status === 404) {
    return <PatientMessage>Patient {id} was not found.</PatientMessage>;
  }

  if (error) {
    return (
      <PatientMessage>
        Could not load patient {id}. {error.message}
      </PatientMessage>
    );
  }

  const { patient, last_encounter, latest } = detail;

  return (
    <main className="main patient">
      <div className="patient__top">
        <TextLink to="/history">Back to history</TextLink>
        <span className="patient__separator" aria-hidden="true">
          /
        </span>
        <span className="patient__label label-mono">Patient dossier:</span>
        <Chip mono>{patient.id}</Chip>
      </div>

      <PatientHeader
        patient={patient}
        lastEncounter={last_encounter ? formatDate(last_encounter) : null}
        protocolComplete={Boolean(latest.right && latest.left)}
        actions={
          <>
            <Button
              variant="secondary"
              icon={Download}
              href={assetUrl(`/patients/${patient.id}/export`)}
            >
              Export Dossier
            </Button>
            <Button icon={Plus} to="/upload">
              New screening
            </Button>
          </>
        }
      />

      <section className="patient__section">
        <h2 className="h2">Latest Bilateral Comparison</h2>
        <p className="patient__section-hint body-rg">
          Most recent screening for each eye.
        </p>
      </section>

      <div className="patient__eyes">
        <EyeSummaryCard eye="right" screening={latest.right} />
        <EyeSummaryCard eye="left" screening={latest.left} />
      </div>

      <InfoNote>
        Each eye is screened, processed, and reported separately to adhere to
        standard bilateral clinical auditing protocols.
      </InfoNote>

      <section className="patient__section">
        <h2 className="h2">All screenings for this patient</h2>
        {screenings && screenings.length > 0 ? (
          <>
            <Table
              label="All screenings for this patient"
              columns={PATIENT_SCREENING_COLUMNS}
              rows={screenings}
              rowHref={(row) => `/results/${row.id}`}
            />
            <p className="patient__count mono-meta">
              {screenings.length}{" "}
              {screenings.length === 1 ? "screening" : "screenings"} total
            </p>
          </>
        ) : (
          <p className="body-md">No screenings for this patient yet.</p>
        )}
      </section>
    </main>
  );
}

export default Patient;
