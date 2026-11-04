import { Link } from "react-router-dom";

function Button({
  variant = "primary",
  icon: Icon,
  fullWidth = false,
  type = "button",
  to,
  href,
  children,
  ...rest
}) {
  const className = `btn-${variant}${fullWidth ? " btn--block" : ""}`;

  const content = (
    <>
      {Icon && <Icon size={20} aria-hidden />}
      {children}
    </>
  );

  if (to) {
    return (
      <Link to={to} className={className} {...rest}>
        {content}
      </Link>
    );
  }

  if (href) {
    return (
      <a href={href} className={className} {...rest}>
        {content}
      </a>
    );
  }

  return (
    <button type={type} className={className} {...rest}>
      {content}
    </button>
  );
}

export default Button;
