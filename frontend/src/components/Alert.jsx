import { AlertTriangle } from "lucide-react";
import "../styles/alert.css";

function Alert({ title, children, actions }) {
  return (
    <div className="alert" role="alert">
      <AlertTriangle size={20} className="alert__icon" aria-hidden />
      <div className="alert__body">
        <h3 className="alert__title body-semibold">{title}</h3>
        <p className="alert__text body-rg">{children}</p>
        {actions && <div className="alert__actions">{actions}</div>}
      </div>
    </div>
  );
}

export default Alert;
