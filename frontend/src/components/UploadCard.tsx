import { useRef, useState } from "react";

import {
  ArrowRight,
  CloudUpload,
} from "lucide-react";


interface UploadCardProps {
  onProcess: (file: File) => void;
}


export default function UploadCard({
  onProcess,
}: UploadCardProps) {

  const inputRef =
    useRef<HTMLInputElement>(null);

  const [file, setFile] =
    useState<File | null>(null);

  const [dragging, setDragging] =
    useState(false);


  const handleFile = (
    selectedFile?: File
  ) => {

    if (!selectedFile) {
      return;
    }


    const valid =
      /\.(csv|xls|xlsx)$/i.test(
        selectedFile.name
      );


    if (!valid) {

      alert(
        "Please select a CSV, XLS or XLSX file."
      );

      return;
    }


    setFile(selectedFile);

  };


  const handleProcess = () => {

    if (!file) {
      return;
    }


    /*
     * IMPORTANT
     *
     * This calls App.tsx.
     *
     * App.tsx changes:
     *
     * UploadCard
     *      ↓
     * ProcessingCard
     */

    onProcess(file);

  };


  return (

    <section className="upload-card">

      {/* HEADER */}

      <div className="upload-heading">

        <h2>
          Upload transaction dataset
        </h2>

        <p>
          Accounts, transactions, channels,
          devices and locations.
        </p>

      </div>


      {/* DROP AREA */}

      <div
        className={`drop-zone ${
          dragging ? "dragging" : ""
        }`}

        onDragOver={(event) => {

          event.preventDefault();

          setDragging(true);

        }}

        onDragLeave={() => {

          setDragging(false);

        }}

        onDrop={(event) => {

          event.preventDefault();

          setDragging(false);

          handleFile(
            event.dataTransfer.files?.[0]
          );

        }}

        onClick={() =>
          inputRef.current?.click()
        }
      >

        <input
          ref={inputRef}
          type="file"
          accept=".csv,.xls,.xlsx"
          hidden

          onChange={(event) =>
            handleFile(
              event.target.files?.[0]
            )
          }
        />


        <div className="upload-icon">

          <CloudUpload
            size={27}
            strokeWidth={1.7}
          />

        </div>


        {file ? (

          <>

            <strong className="selected-file">

              {file.name}

            </strong>


            <span className="file-meta">

              Ready to upload

            </span>

          </>

        ) : (

          <>

            <strong>

              Drag and drop your transaction file

            </strong>


            <span>

              CSV, XLS or XLSX

            </span>

          </>

        )}


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


      {/* UPLOAD & PROCESS */}

      <button

        className={`process-button ${
          !file ? "disabled" : ""
        }`}

        disabled={!file}

        onClick={handleProcess}

      >

        Upload &amp; Process

        <ArrowRight
          size={19}
          strokeWidth={1.8}
        />

      </button>


      {/* EXISTING DATASET */}

      <button

        className="continue-link"

        onClick={() => {

          const demoFile =
            new File(
              [""],
              "Project_Vigilance_Dataset_Password_Protected.xlsx",
              {
                type:
                  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
              }
            );

          onProcess(demoFile);

        }}

      >

        Continue with
        {" "}
        Project_Vigilance_Dataset_Password_Protected.xlsx

        <ArrowRight
          size={14}
        />

      </button>

    </section>

  );
}