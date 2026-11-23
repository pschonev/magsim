import { useEffect, useState } from "react";

const MIN_HEIGHT = 420;
const RESERVED_HEIGHT = 240;
const WIDTH_RATIO = 0.7;

function computeHeight(): number {
  const byViewport = window.innerHeight - RESERVED_HEIGHT;
  const byWidth = window.innerWidth * WIDTH_RATIO;
  return Math.round(Math.max(MIN_HEIGHT, Math.min(byViewport, byWidth)));
}

export function useChartHeight(): number {
  const [height, setHeight] = useState(computeHeight);
  useEffect(() => {
    const onResize = () => setHeight(computeHeight());
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);
  return height;
}
