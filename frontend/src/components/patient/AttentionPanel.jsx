import "../../styles/patient/attention-panel.css";

function AttentionPanel({ imageUrl, eyebrow, icon: Icon, title, description }) {
  return (
    <div className="attention-panel">
      <div className="attention-panel__media">
        {imageUrl ? (
          <img
            className="attention-panel__image"
            src={imageUrl}
            alt={`${title}, fundus photo`}
          />
        ) : (
          <div className="attention-panel__image attention-panel__image--empty" />
        )}
        <span className="attention-panel__tag mono-meta">512px</span>
      </div>

      <div className="attention-panel__text">
        <p className="attention-panel__eyebrow label-mono">
          {Icon ? (
            <Icon size={14} aria-hidden />
          ) : (
            <span className="attention-panel__dot" aria-hidden="true" />
          )}
          {eyebrow}
        </p>
        <h4 className="body-semibold">{title}</h4>
        <p className="attention-panel__description body-rg">{description}</p>
      </div>
    </div>
  );
}

export default AttentionPanel;
