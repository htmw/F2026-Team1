import "../../styles/record/heatmap-tile.css";

function HeatmapTile({ title, description, result, resultLabel, imageUrl }) {
  return (
    <div className="heatmap-tile">
      {imageUrl ? (
        <img
          className="heatmap-tile__image"
          src={imageUrl}
          alt={`${title} overlaid on the fundus photo`}
        />
      ) : (
        <div className="heatmap-tile__image heatmap-tile__image--empty" />
      )}

      <div className="heatmap-tile__text">
        <h3 className="body-semibold">{title}</h3>
        <p className="heatmap-tile__description mono-meta">{description}</p>
        <p
          className={`heatmap-tile__result heatmap-tile__result--${result} mono-meta`}
        >
          Result: {resultLabel}
        </p>
      </div>
    </div>
  );
}

export default HeatmapTile;
