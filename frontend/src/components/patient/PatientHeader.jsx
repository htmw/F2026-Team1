import { User, Venus, Mars, CheckCircle2 } from "lucide-react";
import Card from "../Card.jsx";
import "../../styles/patient/patient-header.css";

const SEX = {
  female: { label: "Female", icon: Venus },
  male: { label: "Male", icon: Mars },
  other: { label: "Other", icon: User },
};

function PatientHeader({ patient, lastEncounter, protocolComplete, actions }) {
  const sex = SEX[patient.sex] ?? SEX.other;
  const SexIcon = sex.icon;

  return (
    <Card>
      <div className="patient-header">
        <div className="patient-header__info">
          <div className="patient-header__name">
            <h1 className="h1">{patient.full_name}</h1>
            <span className="patient-header__id mono-meta">
              ID: {patient.id}
            </span>
          </div>

          <ul className="patient-header__facts body-md">
            <li>
              <User size={16} aria-hidden />
              Age {patient.age}
            </li>
            <li>
              <SexIcon size={16} aria-hidden />
              {sex.label}
            </li>
            {protocolComplete && (
              <li className="patient-header__protocol">
                <CheckCircle2 size={16} aria-hidden />
                Bilateral Protocol Complete
              </li>
            )}
          </ul>

          {lastEncounter && (
            <p className="patient-header__encounter caption-rg">
              Last Encounter: {lastEncounter}
            </p>
          )}
        </div>

        {actions && <div className="patient-header__actions">{actions}</div>}
      </div>
    </Card>
  );
}

export default PatientHeader;
