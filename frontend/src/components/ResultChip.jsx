import { CheckCircle2, AlertTriangle, HelpCircle } from "lucide-react";
import Chip from "./Chip.jsx";

const RESULTS = {
  no_concern: {
    tone: "success",
    icon: CheckCircle2,
    label: "No concern",
  },
  refer: {
    tone: "danger",
    icon: AlertTriangle,
    label: "Refer",
  },
  uncertain: {
    tone: "warning",
    icon: HelpCircle,
    label: "Uncertain, refer",
  },
};

function ResultChip({ result }) {
  const { tone, icon, label } = RESULTS[result];
  return (
    <Chip tone={tone} icon={icon}>
      {label}
    </Chip>
  );
}

export default ResultChip;
