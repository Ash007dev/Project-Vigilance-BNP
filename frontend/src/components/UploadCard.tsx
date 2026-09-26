// Target path: frontend/src/components/UploadCard.tsx
//
// The dashed dropzone itself -- just the drop target, no surrounding card
// chrome (title/subtitle/button live in Upload.tsx, which wraps this in
// its own white card). Kept separate so this widget stays reusable if you
// ever need a file drop zone somewhere else.

import React, { useState } from "react";
import { UploadCloudIcon } from "./Icons";

interface UploadCardProps {
  file: File | null;
  onFileSelected: (file: File | null) => void;
}

export default function UploadCard({ file, onFileSelected }: UploadCardProps) {
  const [dragOver, setDragOver] = useState(false);

  function handleDrop(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragOver(false);
    const dropped = e.dataTransfer.files?.[0];
    if (dropped) onFileSelected(dropped);
  }

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      style={{
        textAlign: "center",
        padding: "40px 24px",
        borderRadius: 10,
        border: `2px dashed ${dragOver ? "var(--color-primary)" : "var(--color-border)"}`,
        backgroundColor: dragOver ? "var(--color-primary-light)" : "var(--color-bg-subtle)",
        transition: "border-color 0.15s ease, background-color 0.15s ease",
      }}
    >
      <div className="icon-circle" style={{ margin: "0 auto 16px" }}>
        <UploadCloudIcon size={22} />
      </div>

      <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 4 }}>
        {file ? file.name : "Drag and drop your transaction file"}
      </div>
      <div style={{ fontSize: 13, color: "var(--color-text-muted)", marginBottom: 20 }}>
        {file ? `${(file.size / 1024).toFixed(1)} KB` : "CSV, XLS or XLSX"}
      </div>

      <button
        type="button"
        className="secondary"
        onClick={() => document.getElementById("file-input")?.click()}
      >
        Browse Files
      </button>

      <input
        id="file-input"
        type="file"
        accept=".csv,.xls,.xlsx"
        style={{ display: "none" }}
        onChange={(e) => onFileSelected(e.target.files?.[0] ?? null)}
      />
    </div>
  );
}
