import { useCallback, useState } from "react";
import { InfoTip } from "../../components/InfoTip";
import type { RacerDistributionsDTO } from "../../types/api";
import { displayName } from "../../utils/names";
import { MIN_RACES, averageText } from "./charts/distributionCharts";
import { type BinHover, DistributionTip } from "./DistributionTip";
import { BIN_TIP_GROUP, TriggerHistogram } from "./DistributionBars";
import { useRowHeight, useWidth } from "./useChartBox";
import { useDismissTip } from "./useDismissTip";

/** Card padding and the title row; the chart gets the rest of the card's height. */
const CARD_CHROME = 64;

interface TriggerDistributionProps {
  racerName: string;
  /** Theme-adjusted racer colour. */
  ink: string;
  distributions: RacerDistributionsDTO;
}

/** The racer's ability triggers per race, for the races left by the dashboard filters. */
export function TriggerDistribution({ racerName, ink, distributions }: TriggerDistributionProps) {
  const [hover, setHover] = useState<BinHover | null>(null);
  const clearHover = useCallback(() => setHover(null), []);
  useDismissTip(BIN_TIP_GROUP, hover !== null, clearHover);
  const { ref: cardRef, height } = useRowHeight(racerName);
  const { ref: chartRef, width } = useWidth();
  const racer = distributions.racers.find((r) => r.racer_name === racerName);
  const labels = distributions.trigger_labels;
  const name = displayName(racerName);
  return (
    <div
      ref={cardRef}
      className="flex flex-col gap-1 rounded-lg border border-slate-700 bg-slate-900 p-3"
      style={racer ? { height } : undefined}
    >
      <div className="flex items-center gap-1.5">
        <h3 className="text-xs font-semibold text-slate-100">Ability triggers per race</h3>
        <InfoTip label="More about ability triggers per race">
          <p>
            Follows the dashboard filters, unlike the roses: only the races left by the filters are counted.
          </p>
          <p>
            Each bar is the share of this racer&apos;s races with that many ability triggers. All racers use the same
            x range; the last bin (≥) collects every race with that many triggers or more.
          </p>
          <p>Racers with fewer than {MIN_RACES} races are not shown.</p>
        </InfoTip>
        {racer && (
          <span className="ml-auto text-[11px] font-semibold" style={{ color: ink }}>
            {averageText(racer.mean_triggers)}
          </span>
        )}
      </div>
      <div ref={chartRef} className="min-h-0 flex-1">
        {racer && width > 0 && (
          <TriggerHistogram
            width={width}
            height={Math.max(height - CARD_CHROME, 1)}
            label={`${name}: share of races by ability triggers`}
            labels={labels}
            axisTitle="ability triggers"
            racer={racer.triggers}
            color={ink}
            onHover={(hit) =>
              setHover(hit && { label: labels[hit.bin], racerShare: racer.triggers[hit.bin], x: hit.x, y: hit.y })
            }
          />
        )}
        {!racer && (
          <p className="text-[11px] text-slate-500">
            Fewer than {MIN_RACES} races with the current filters, so there is no distribution to show.
          </p>
        )}
      </div>
      {hover && <DistributionTip hover={hover} racerName={name} ink={ink} />}
    </div>
  );
}
