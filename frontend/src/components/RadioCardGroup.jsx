import "../styles/radio-card-group.css";

function RadioCardGroup({ name, options, value, onChange, ...rest }) {
  return (
    <div className="radio-cards" role="radiogroup" {...rest}>
      {options.map((option) => (
        <label key={option.value} className="radio-card body-md">
          <input
            className="radio-card__input"
            type="radio"
            name={name}
            value={option.value}
            checked={value === option.value}
            onChange={() => onChange(option.value)}
          />
          <span className="radio-card__dot" aria-hidden></span>
          {option.label}
        </label>
      ))}
    </div>
  );
}

export default RadioCardGroup;
