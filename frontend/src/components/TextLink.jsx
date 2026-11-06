import { Link } from "react-router-dom";
import "../styles/text-link.css";

function TextLink({
  to,
  leadingIcon: LeadingIcon,
  trailingIcon: TrailingIcon,
  strong = false,
  accent = false,
  children,
}) {
  const className = [
    "text-link",
    strong && "text-link--strong",
    accent && "text-link--accent",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <Link to={to} className={className}>
      {LeadingIcon && <LeadingIcon size={16} aria-hidden="true" />}
      {children}
      {TrailingIcon && <TrailingIcon size={16} aria-hidden="true" />}
    </Link>
  );
}

export default TextLink;
