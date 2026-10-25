"use client";

import { useCallback, useRef, useState } from "react";

interface RfpPdfDropzoneProps {
  disabled?: boolean;
  onFileSelected: (file: File) => void;
}

function isPdfFile(file: File): boolean {
  const name = file.name.toLowerCase();
  return name.endsWith(".pdf") || file.type === "application/pdf";
}

export function RfpPdfDropzone({
  disabled = false,
  onFileSelected,
}: RfpPdfDropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const [selectedName, setSelectedName] = useState<string | null>(null);

  const acceptFile = useCallback(
    (file: File | undefined) => {
      if (!file) return;
      if (!isPdfFile(file)) {
        setLocalError("Only PDF files are accepted.");
        setSelectedName(null);
        return;
      }
      if (file.size === 0) {
        setLocalError("The selected file is empty.");
        setSelectedName(null);
        return;
      }
      if (file.size > 25 * 1024 * 1024) {
        setLocalError("PDF exceeds the 25 MB limit.");
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
        aria-label="Upload RFP PDF"
        onKeyDown={(event) => {
          if (disabled) return;
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            inputRef.current?.click();
          }
        }}
        onClick={() => {
          if (!disabled) inputRef.current?.click();
        }}
        onDragEnter={(event) => {
          event.preventDefault();
          if (!disabled) setIsDragging(true);
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
          if (disabled) return;
          acceptFile(event.dataTransfer.files?.[0]);
        }}
        className={`rounded-xl border-2 border-dashed px-4 py-8 text-center transition ${
          disabled
            ? "cursor-not-allowed border-slate-200 bg-slate-100 opacity-70 dark:border-slate-700"
            : isDragging
              ? "cursor-pointer border-blue-400 bg-blue-50 dark:bg-blue-950/40"
              : "cursor-pointer border-slate-300 bg-white hover:border-blue-300 hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-900 dark:hover:bg-slate-800"
        }`}
      >
        <p className="text-sm font-medium text-slate-800 dark:text-slate-100">
          Drag and drop an RFP PDF here, or click to browse
        </p>
        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
          Institutional RFPs only · max 25 MB · field <code>file</code>
        </p>
        {selectedName ? (
          <p className="mt-3 text-sm text-blue-700 dark:text-blue-300">
            Selected: {selectedName}
          </p>
        ) : null}
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf,.pdf"
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
