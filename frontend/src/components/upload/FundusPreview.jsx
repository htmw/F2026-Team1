import { ImageIcon } from "lucide-react";
import Card from "../Card.jsx";
import "../../styles/upload/fundus-preview.css";

function FundusPreview({ src }) {
  return (
    <Card
      title="Fundus Preview"
      aside={src ? "Direct preview" : "Awaiting capture"}
    >
      <div className="fundus-preview">
        {src ? (
          <img
            className="fundus-preview__img"
            src={src}
            alt="Uploaded fundus photograph preview"
          />
        ) : (
          <div className="fundus-preview__empty">
            <ImageIcon size={32} className="fundus-preview__icon" aria-hidden />
            <p className="body-md">No photo loaded yet</p>
            <p className="caption-rg fundus-preview__hint">
              Select a patient and upload a fundus photo
            </p>
          </div>
        )}
      </div>
    </Card>
  );
}

export default FundusPreview;
