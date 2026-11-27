import { useEffect } from "react";

/** Props that mark an element as showing a tooltip of this group when pressed (touch has no mouse leave to hide it). */
export const tipTarget = (group: string) => ({ "data-tip-target": group });

/** While `active`, a press outside every tooltip target of the group calls `onDismiss`. */
export function useDismissTip(group: string, active: boolean, onDismiss: () => void): void {
  useEffect(() => {
    if (!active) return;
    const onPress = (e: PointerEvent) => {
      if (e.target instanceof Element && e.target.closest(`[data-tip-target="${group}"]`)) return;
      onDismiss();
    };
    document.addEventListener("pointerdown", onPress);
    return () => document.removeEventListener("pointerdown", onPress);
  }, [group, active, onDismiss]);
}
