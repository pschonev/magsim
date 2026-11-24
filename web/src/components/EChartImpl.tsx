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
import { CanvasRenderer } from "echarts/renderers";
import { useEffect, useRef } from "react";

const CHART_FONT = 'ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif';

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
  CanvasRenderer,
]);

export type EChartsOption = echarts.EChartsCoreOption;

export interface EChartProps {
  option: EChartsOption;
  height?: number | string;
  className?: string;
  onClick?: (params: Record<string, unknown>) => void;
  onChartReady?: (chart: echarts.ECharts) => (() => void) | undefined;
}

export function EChartImpl({
  option,
  height = 420,
  className = "",
  onClick,
  onChartReady,
}: EChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const instanceRef = useRef<echarts.ECharts | null>(null);
  const onClickRef = useRef(onClick);
  onClickRef.current = onClick;
  const onReadyRef = useRef(onChartReady);
  onReadyRef.current = onChartReady;

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const chart = echarts.init(el, undefined, { renderer: "canvas" });
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
  }, []);

  useEffect(() => {
    const chart = instanceRef.current;
    if (!chart) return;
    chart.setOption({ textStyle: { fontFamily: CHART_FONT }, ...option }, { notMerge: true, lazyUpdate: true });
    chart.resize();
  }, [option, height]);

  return (
    <div
      ref={containerRef}
      style={{
        height: typeof height === "number" ? `${height}px` : height,
        width: "100%",
      }}
      className={className}
    />
  );
}
