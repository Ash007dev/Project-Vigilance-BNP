import { ArrowRight, CloudUpload } from "lucide-react";
import { useRef, useState } from "react";


type UploadCardProps = {
  onProcess: (file: File) => void;
  onContinue: () => void;
};

const acceptedFile = /\.(csv|xls|xlsx)$/i;

export default function UploadCard({ onProcess, onContinue }: UploadCardProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);

  function selectFile(selectedFile?: File) {
    if (!selectedFile) return;
    if (!acceptedFile.test(selectedFile.name)) {
      window.alert("Please select a CSV, XLS, or XLSX file.");
      return;
    }
    setFile(selectedFile);
  }

  return (
    <section className="upload-card">
      <div className="upload-heading">
        <h2>Upload transaction dataset</h2>
        <p>Accounts, transactions, channels, devices, and locations.</p>
      </div>

      <div
        className={`drop-zone ${dragging ? "dragging" : ""}`}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          selectFile(event.dataTransfer.files?.[0]);
        }}
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".csv,.xls,.xlsx"
          hidden
          onChange={(event) => selectFile(event.target.files?.[0])}
        />
        <div className="upload-icon"><CloudUpload size={27} strokeWidth={1.7} /></div>
        <strong className={file ? "selected-file" : ""}>
          {file?.name ?? "Drag and drop your transaction file"}
        </strong>
        <span>{file ? "Ready to upload" : "CSV, XLS, or XLSX"}</span>
        <button
          type="button"
          className="browse-button"
          onClick={(event) => {
            event.stopPropagation();
            inputRef.current?.click();
          }}
        >
          Browse Files
        </button>
      </div>

      <button
        type="button"
        className={`process-button ${file ? "" : "disabled"}`}
        disabled={!file}
        onClick={() => file && onProcess(file)}
      >
        Upload &amp; Process <ArrowRight size={19} />
      </button>

      <button type="button" className="continue-link" onClick={onContinue}>
        Continue with the data already in PostgreSQL <ArrowRight size={14} />
      </button>
    </section>
  );
}
