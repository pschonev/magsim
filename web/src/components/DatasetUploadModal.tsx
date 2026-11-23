import { Upload, X } from "lucide-react";
import { useState } from "react";

interface DatasetUploadModalProps {
  open: boolean;
  onClose: () => void;
  onUpload: (
    racesBytes: Uint8Array,
    resultsBytes: Uint8Array,
    format: "ipc" | "parquet",
  ) => Promise<void>;
}

export function DatasetUploadModal({
  open,
  onClose,
  onUpload,
}: DatasetUploadModalProps) {
  const [racesFile, setRacesFile] = useState<File | null>(null);
  const [resultsFile, setResultsFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!open) return null;

  const detectFormat = (file: File): "ipc" | "parquet" => {
    const lower = file.name.toLowerCase();
    return lower.endsWith(".ipc") || lower.endsWith(".feather")
      ? "ipc"
      : "parquet";
  };

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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl">
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Upload className="h-4 w-4 text-indigo-400" />
            <h2 className="text-base font-semibold text-slate-50">
              Load Custom Dataset
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-slate-50"
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
              type="file"
              accept=".ipc,.feather,.parquet"
              onChange={(e) => setRacesFile(e.target.files?.[0] ?? null)}
              className="block w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-200 file:mr-3 file:rounded file:border-0 file:bg-indigo-600 file:px-2.5 file:py-1 file:text-xs file:font-medium file:text-white hover:file:bg-indigo-500"
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
              className="block w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-200 file:mr-3 file:rounded file:border-0 file:bg-indigo-600 file:px-2.5 file:py-1 file:text-xs file:font-medium file:text-white hover:file:bg-indigo-500"
            />
          </label>

          {error && (
            <div className="rounded-lg border border-rose-500/40 bg-rose-950/50 p-2.5 text-xs text-rose-200">
              {error}
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="rounded-lg border border-slate-700 px-3.5 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-800"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSubmit}
              disabled={loading || !racesFile || !resultsFile}
              className="rounded-lg bg-indigo-600 px-4 py-1.5 text-xs font-medium text-on-accent hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? "Loading dataset..." : "Load Dataset"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
