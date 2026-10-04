function Chip({ tone = "neutral", icon: Icon, mono = false, children }) {
  return (
    <span className={`chip chip--${tone}${mono ? " chip--mono" : ""}`}>
      {Icon && <Icon size={14} aria-hidden />}
      {children}
    </span>
  );
}

export default Chip;
