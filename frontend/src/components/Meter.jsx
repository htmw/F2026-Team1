import "../styles/record/meter.css";

function clamp(value) {
  return Math.min(Math.max(value, 0), 1);
}

function Meter({ value, marker, result, label }) {
  return (
    <div
      className="meter"
      role="img"
      aria-label={`${label}: ${Math.round(value * 100)}%`}
    >
      <div
        className={`meter__fill meter__fill--${result}`}
        style={{ width: `${clamp(value) * 100}%` }}
      />
      {marker !== undefined && (
        <div
          className="meter__marker"
          style={{ left: `${clamp(marker) * 100}%` }}
        />
      )}
    </div>
  );
}

export default Meter;
