import { Info } from "lucide-react";
import "../styles/info-note.css";

function InfoNote({ icon: Icon = Info, children }) {
  return (
    <div className="info-note" role="note">
      <Icon size={20} className="info-note__icon" aria-hidden />
      <p className="info-note__text body-rg">{children}</p>
    </div>
  );
}

export default InfoNote;
