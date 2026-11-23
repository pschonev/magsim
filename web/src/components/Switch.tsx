interface SwitchProps {
  label: string;
  checked: boolean;
  onChange: (next: boolean) => void;
}

export function Switch({ label, checked, onChange }: SwitchProps) {
  return (
    <label className="inline-flex cursor-pointer items-center gap-2 text-xs text-slate-300">
      <input
        type="checkbox"
        role="switch"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="h-3.5 w-3.5 accent-indigo-500"
      />
      {label}
    </label>
  );
}
