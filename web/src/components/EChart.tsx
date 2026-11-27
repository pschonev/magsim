import { lazy, Suspense } from "react";
import type { EChartProps } from "./EChartImpl";

export type { EChartsOption } from "./EChartImpl";

const LazyEChart = lazy(async () => ({
  default: (await import("./EChartImpl")).EChartImpl,
}));

export function EChart(props: EChartProps) {
  const height = props.height ?? 420;
  return (
    <Suspense
      fallback={
        <div
          style={{ height: typeof height === "number" ? `${height}px` : height }}
          className="flex items-center justify-center text-xs text-slate-500"
        >
          Loading chart...
        </div>
      }
    >
      <LazyEChart {...props} />
    </Suspense>
  );
}
