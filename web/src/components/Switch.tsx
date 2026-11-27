interface SwitchProps {
  label: string;
  checked: boolean;
  onChange: (next: boolean) => void;
}

export function Switch({ label, checked, onChange }: SwitchProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className="inline-flex cursor-pointer items-center gap-2 text-left text-xs text-slate-300 max-sm:min-h-9 pointer-coarse:min-h-9"
    >
      <span
        className={`relative inline-block h-4 w-7 shrink-0 rounded-full transition-colors ${
          checked ? "bg-indigo-600" : "bg-slate-700"
        }`}
      >
        <span
          className={`absolute top-0.5 left-0.5 h-3 w-3 rounded-full bg-white shadow transition-transform ${
            checked ? "translate-x-3" : ""
          }`}
        />
      </span>
      {label}
    </button>
  );
}
