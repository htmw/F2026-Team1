function Chip({ tone = "neutral", icon: Icon, mono = false, children }) {
  return (
    <span className={`chip chip--${tone}${mono ? " chip--mono" : ""}`}>
      {Icon && <Icon />}
      {children}
    </span>
  );
}

export default Chip;
