import { useState } from "react";
import { Check, CloudUpload } from "lucide-react";
import Chip from "../Chip.jsx";
import "../../styles/upload/file-dropzone.css";

const ACCEPTED_TYPES = ["image/jpeg", "image/png"];

function FileDropzone({ file, onFile }) {
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState("");

  function handleFile(selectedFile) {
    if (!selectedFile) return;

    if (!ACCEPTED_TYPES.includes(selectedFile.type)) {
      setError("Only JPG or PNG photos are accepted.");
      return;
    }

    setError("");
    onFile(selectedFile);
  }

  function handleChange(e) {
    handleFile(e.target.files[0]);
  }

  function handleDragOver(e) {
    e.preventDefault();
    setIsDragging(true);
  }

  function handleDragLeave() {
    setIsDragging(false);
  }

  function handleDrop(e) {
    e.preventDefault();
    setIsDragging(false);
    handleFile(e.dataTransfer.files[0]);
  }

  return (
    <div>
      <label
        className={`dropzone${isDragging ? " dropzone--dragging" : ""}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <input
          className="dropzone__input"
          type="file"
          accept="image/jpeg,image/png"
          onChange={handleChange}
        />
        <span className="dropzone__icon">
          <CloudUpload size={24} aria-hidden />
        </span>
        <span className="body-semibold">Select fundus image</span>
        <span className="caption-rg dropzone__hint">
          Drag and drop the acquired fundus capture here or click to browse
        </span>
        {file ? (
          <Chip tone="success" icon={Check} mono>
            {file.name}
          </Chip>
        ) : (
          <Chip mono>JPG OR PNG</Chip>
        )}
      </label>

      {error && (
        <p className="caption-md dropzone__error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

export default FileDropzone;
