import { InfoTip } from "../../components/InfoTip";

const EXPLANATION = "Computed from all races of the bundled dataset; the dashboard filters do not change it.";

/** Muted pill for numbers that ignore the dashboard filters; the hover or tap text says why. */
export function FilterScopeBadge() {
  return (
    <span
      title={EXPLANATION}
      className="inline-flex items-center gap-1 rounded-full border border-slate-700 px-2 py-0.5 text-[11px] whitespace-nowrap text-slate-400"
    >
      Filters don&apos;t apply
      <InfoTip label="Why the filters do not apply">
        <p>{EXPLANATION}</p>
      </InfoTip>
    </span>
  );
}
