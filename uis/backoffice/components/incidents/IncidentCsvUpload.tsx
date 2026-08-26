"use client";

import { useCallback, useRef, useState } from "react";

interface IncidentCsvUploadProps {
  disabled?: boolean;
  onFileSelected: (file: File) => void;
}

function isCsvFile(file: File): boolean {
  return file.name.toLowerCase().endsWith(".csv");
}

export function IncidentCsvUpload({
  disabled = false,
  onFileSelected,
}: IncidentCsvUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const [selectedName, setSelectedName] = useState<string | null>(null);

  const acceptFile = useCallback(
    (file: File | undefined) => {
      if (!file) {
        return;
      }
      if (!isCsvFile(file)) {
        setLocalError("Please select a .csv file.");
        setSelectedName(null);
        return;
      }
      if (file.size === 0) {
        setLocalError("The selected file is empty.");
        setSelectedName(null);
        return;
      }
      setLocalError(null);
      setSelectedName(file.name);
      onFileSelected(file);
    },
    [onFileSelected]
  );

  return (
    <div className="space-y-2">
      <div
        role="button"
        tabIndex={0}
        aria-disabled={disabled}
        onKeyDown={(event) => {
          if (disabled) {
            return;
          }
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            inputRef.current?.click();
          }
        }}
        onClick={() => {
          if (!disabled) {
            inputRef.current?.click();
          }
        }}
        onDragEnter={(event) => {
          event.preventDefault();
          if (!disabled) {
            setIsDragging(true);
          }
        }}
        onDragOver={(event) => {
          event.preventDefault();
        }}
        onDragLeave={(event) => {
          event.preventDefault();
          setIsDragging(false);
        }}
        onDrop={(event) => {
          event.preventDefault();
          setIsDragging(false);
          if (disabled) {
            return;
          }
          acceptFile(event.dataTransfer.files?.[0]);
        }}
        className={`rounded-xl border-2 border-dashed px-4 py-8 text-center transition ${
          disabled
            ? "cursor-not-allowed border-slate-200 dark:border-slate-700 bg-slate-100 opacity-70"
            : isDragging
              ? "cursor-pointer border-blue-400 bg-blue-50"
              : "cursor-pointer border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 hover:border-blue-300 hover:bg-slate-50 dark:hover:bg-slate-800"
        }`}
      >
        <p className="text-sm font-medium text-slate-800 dark:text-slate-100">
          Drag and drop a CSV file here, or click to browse
        </p>
        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
          Field name sent to the API: <code>file</code> (multipart/form-data)
        </p>
        {selectedName ? (
          <p className="mt-3 text-sm text-blue-700 dark:text-blue-300">Selected: {selectedName}</p>
        ) : null}
        <input
          ref={inputRef}
          type="file"
          accept=".csv,text/csv"
          className="hidden"
          disabled={disabled}
          onChange={(event) => {
            acceptFile(event.target.files?.[0]);
            event.target.value = "";
          }}
        />
      </div>
      {localError ? (
        <p className="text-sm text-red-600 dark:text-red-400" role="alert">
          {localError}
        </p>
      ) : null}
    </div>
  );
}
