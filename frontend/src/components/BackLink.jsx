import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import "../styles/back-link.css";

function BackLink({ to, children }) {
  return (
    <Link to={to} className="back-link">
      <ArrowLeft size={16} aria-hidden="true" />
      {children}
    </Link>
  );
}

export default BackLink;
