import { useEffect, useState } from "react";

/** The screen's pixel ratio; updates when the window moves between screens or the browser zoom changes. */
export function useDevicePixelRatio(): number {
  const [ratio, setRatio] = useState(() => window.devicePixelRatio);
  useEffect(() => {
    const media = window.matchMedia(`(resolution: ${ratio}dppx)`);
    const update = () => setRatio(window.devicePixelRatio);
    media.addEventListener("change", update, { once: true });
    return () => media.removeEventListener("change", update);
  }, [ratio]);
  return ratio;
}
