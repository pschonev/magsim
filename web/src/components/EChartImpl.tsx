import { BarChart, HeatmapChart, LineChart, PieChart, ScatterChart } from "echarts/charts";
import {
  DataZoomComponent,
  GraphicComponent,
  GridComponent,
  LegendComponent,
  MarkAreaComponent,
  MarkLineComponent,
  TitleComponent,
  TooltipComponent,
  VisualMapComponent,
} from "echarts/components";
import * as echarts from "echarts/core";
import { LabelLayout } from "echarts/features";
import { CanvasRenderer, SVGRenderer } from "echarts/renderers";
import { useEffect, useRef } from "react";
import { CHART_FONT } from "../utils/chartFont";
import { useDevicePixelRatio } from "../utils/useDevicePixelRatio";

echarts.use([
  ScatterChart,
  BarChart,
  LineChart,
  PieChart,
  HeatmapChart,
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent,
  VisualMapComponent,
  MarkLineComponent,
  MarkAreaComponent,
  DataZoomComponent,
  GraphicComponent,
  LabelLayout,
  CanvasRenderer,
  SVGRenderer,
]);

export type EChartsOption = echarts.EChartsCoreOption;

type TooltipOption = Record<string, unknown>;

/** Tooltips live on `document.body`, so neighbouring charts and `overflow: hidden` cards never cover or clip them. */
function withBodyTooltip(unit: Record<string, unknown>): Record<string, unknown> {
  const tooltip = unit.tooltip as TooltipOption | TooltipOption[] | undefined;
  if (!tooltip || Array.isArray(tooltip)) return unit;
  return { ...unit, tooltip: { appendToBody: true, ...tooltip } };
}

/** Applies the shared defaults to a plain option or to the `baseOption` of a responsive (`media`) option. */
function withDefaults(option: EChartsOption): EChartsOption {
  const unit = option as Record<string, unknown>;
  const defaults = { textStyle: { fontFamily: CHART_FONT } };
  const base = unit.baseOption as Record<string, unknown> | undefined;
  if (base) return { ...unit, baseOption: withBodyTooltip({ ...defaults, ...base }) };
  return withBodyTooltip({ ...defaults, ...unit });
}

export interface EChartProps {
  option: EChartsOption;
  height?: number | string;
  className?: string;
  /** SVG keeps text crisp at any zoom or pixel ratio; canvas is faster for big data (heatmaps). */
  renderer?: "canvas" | "svg";
  onClick?: (params: Record<string, unknown>) => void;
  onChartReady?: (chart: echarts.ECharts) => (() => void) | undefined;
}

export function EChartImpl({
  option,
  height = 420,
  className = "",
  renderer = "canvas",
  onClick,
  onChartReady,
}: EChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const instanceRef = useRef<echarts.ECharts | null>(null);
  const onClickRef = useRef(onClick);
  onClickRef.current = onClick;
  const onReadyRef = useRef(onChartReady);
  onReadyRef.current = onChartReady;
  const screenRatio = useDevicePixelRatio();
  // Only the canvas bitmap depends on the pixel ratio: SVG is vector and never needs a re-init for it.
  const pixelRatio = renderer === "canvas" ? screenRatio : 1;

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const chart = echarts.init(el, undefined, { renderer, devicePixelRatio: pixelRatio });
    instanceRef.current = chart;

    const handleClick = (params: Record<string, unknown>) => {
      onClickRef.current?.(params);
    };
    chart.on("click", handleClick);
    const detach = onReadyRef.current?.(chart);

    const observer = new ResizeObserver(() => {
      chart.resize();
    });
    observer.observe(el);

    return () => {
      observer.disconnect();
      detach?.();
      chart.off("click", handleClick);
      chart.dispose();
      instanceRef.current = null;
    };
  }, [renderer, pixelRatio]);

  useEffect(() => {
    const chart = instanceRef.current;
    if (!chart) return;
    chart.setOption(withDefaults(option), { notMerge: true, lazyUpdate: true });
    chart.resize();
  }, [option, height, renderer, pixelRatio]);

  return (
    <div
      ref={containerRef}
      style={{
        height: typeof height === "number" ? `${height}px` : height,
        width: "100%",
        minWidth: 0,
        // The chart follows its container's width and never contributes to it, so a wide chart cannot keep a grid track wide.
        contain: "inline-size",
      }}
      className={className}
    />
  );
}
