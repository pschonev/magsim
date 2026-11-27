import { percent, triggersLabel } from "./charts/distributionCharts";
import { FloatingTip } from "./FloatingTip";

/** What the pointer is over: one bin of the triggers chart. */
export interface BinHover {
  /** The bin's label, e.g. "3" or "≥12". */
  label: string;
  racerShare: number;
  x: number;
  y: number;
}

interface DistributionTipProps {
  hover: BinHover;
  racerName: string;
  /** Theme-adjusted racer colour. */
  ink: string;
}

export function DistributionTip({ hover, racerName, ink }: DistributionTipProps) {
  const { label, racerShare, x, y } = hover;
  return (
    <FloatingTip x={x} y={y}>
      <span className="font-semibold" style={{ color: ink }}>
        {racerName}
      </span>{" "}
      · {triggersLabel(label)} · {percent(racerShare)} of races
    </FloatingTip>
  );
}
