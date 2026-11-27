import { Loader2, Upload, X } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";
import type { StageStatus } from "../types/api";

interface DatasetUploadModalProps {
  open: boolean;
  /** Uploading needs the Python engine; the submit button waits until it is ready. */
  engineStatus: StageStatus;
  onClose: () => void;
  onUpload: (
    racesBytes: Uint8Array,
    resultsBytes: Uint8Array,
    format: "ipc" | "parquet",
  ) => Promise<void>;
}

const FILE_INPUT_CLASS =
  "block w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-200 file:mr-3 file:rounded file:border-0 file:bg-indigo-600 file:px-2.5 file:py-1 file:text-xs file:font-medium file:text-white hover:file:bg-indigo-500";

const detectFormat = (file: File): "ipc" | "parquet" => {
  const lower = file.name.toLowerCase();
  return lower.endsWith(".ipc") || lower.endsWith(".feather") ? "ipc" : "parquet";
};

function UploadDialog({ engineStatus, onClose, onUpload }: Omit<DatasetUploadModalProps, "open">) {
  const engineReady = engineStatus === "ready";
  const engineFailed = engineStatus === "error";
  const titleId = useId();
  const firstInputRef = useRef<HTMLInputElement | null>(null);
  const [racesFile, setRacesFile] = useState<File | null>(null);
  const [resultsFile, setResultsFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const close = () => {
    if (!loading) onClose();
  };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !loading) onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose, loading]);

  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    firstInputRef.current?.focus();
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, []);

  const handleSubmit = async () => {
    if (!racesFile || !resultsFile) {
      setError("Please select both a races file and a racer_results file.");
      return;
    }
    const fmtA = detectFormat(racesFile);
    const fmtB = detectFormat(resultsFile);
    if (fmtA !== fmtB) {
      setError("Both files must use the same format (.ipc or .parquet).");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const [rb, rrb] = await Promise.all([
        racesFile.arrayBuffer(),
        resultsFile.arrayBuffer(),
      ]);
      await onUpload(new Uint8Array(rb), new Uint8Array(rrb), fmtA);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/70 p-2 backdrop-blur-sm sm:p-4"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) close();
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="my-auto w-full max-w-lg rounded-2xl border border-slate-700 bg-slate-900 p-4 shadow-2xl sm:p-6"
      >
        <div className="mb-4 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Upload className="h-4 w-4 text-indigo-400" />
            <h2 id={titleId} className="text-base font-semibold text-slate-50">
              Load Custom Dataset
            </h2>
          </div>
          <button
            type="button"
            onClick={close}
            aria-label="Close dialog"
            className="inline-flex h-10 w-10 items-center justify-center rounded-lg text-slate-400 hover:bg-slate-800 hover:text-slate-50 sm:h-8 sm:w-8 pointer-coarse:h-10 pointer-coarse:w-10"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <p className="mb-4 text-xs text-slate-400">
          Upload a matching pair of <code className="text-slate-200">.ipc</code>{" "}
          (fastest) or <code className="text-slate-200">.parquet</code>{" "}
          (auto-loads <code className="text-slate-200">pyarrow</code> on demand)
          simulation exports.
        </p>

        <div className="space-y-3">
          <label className="block">
            <span className="mb-1 block text-xs font-medium text-slate-300">
              Races file (races.zstd.ipc / races.parquet)
            </span>
            <input
              ref={firstInputRef}
              type="file"
              accept=".ipc,.feather,.parquet"
              onChange={(e) => setRacesFile(e.target.files?.[0] ?? null)}
              className={FILE_INPUT_CLASS}
            />
          </label>

          <label className="block">
            <span className="mb-1 block text-xs font-medium text-slate-300">
              Racer Results file (racer_results.zstd.ipc / racer_results.parquet)
            </span>
            <input
              type="file"
              accept=".ipc,.feather,.parquet"
              onChange={(e) => setResultsFile(e.target.files?.[0] ?? null)}
              className={FILE_INPUT_CLASS}
            />
          </label>

          {error && (
            <div role="alert" className="rounded-lg border border-rose-500/40 bg-rose-950/50 p-2.5 text-xs text-rose-200">
              {error}
            </div>
          )}
          {engineFailed && (
            <div role="alert" className="rounded-lg border border-rose-500/40 bg-rose-950/50 p-2.5 text-xs text-rose-200">
              The Python engine failed to start. Close this dialog and retry from the Simulator tab, or reload the page.
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={close}
              disabled={loading}
              className="rounded-lg border border-slate-700 px-3.5 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-800 max-sm:min-h-10 pointer-coarse:min-h-10"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSubmit}
              disabled={loading || !engineReady || !racesFile || !resultsFile}
              className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-4 py-1.5 text-xs font-medium text-on-accent hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50 max-sm:min-h-10 pointer-coarse:min-h-10"
            >
              {engineStatus === "loading" || engineStatus === "idle" ? (
                <>
                  <Loader2 className="h-3 w-3 motion-safe:animate-spin" />
                  Starting engine…
                </>
              ) : loading ? (
                "Loading dataset..."
              ) : (
                "Load Dataset"
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

/** Dialog for loading a custom races / racer_results pair. */
export function DatasetUploadModal({ open, engineStatus, onClose, onUpload }: DatasetUploadModalProps) {
  if (!open) return null;
  return <UploadDialog engineStatus={engineStatus} onClose={onClose} onUpload={onUpload} />;
}
