function Button({
  variant = "primary",
  icon: Icon,
  fullWidth = false,
  type = "button",
  children,
  ...rest
}) {
  return (
    <button
      type={type}
      className={`btn-${variant}${fullWidth ? " btn--block" : ""}`}
      {...rest}
    >
      {Icon && <Icon size={20} aria-hidden />}
      {children}
    </button>
  );
}

export default Button;
