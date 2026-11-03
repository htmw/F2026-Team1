import { Link } from "react-router-dom";
import { ArrowLeft, ChevronRight } from "lucide-react";
import "../styles/text-link.css";

function TextLink({
  to,
  leadingArrow = false,
  trailingArrow = false,
  strong = false,
  children,
}) {
  return (
    <Link to={to} className={`text-link${strong ? " text-link--strong" : ""}`}>
      {leadingArrow && <ArrowLeft size={16} aria-hidden="true" />}
      {children}
      {trailingArrow && <ChevronRight size={16} aria-hidden="true" />}
    </Link>
  );
}

export default TextLink;
