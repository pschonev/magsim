import type { ReactNode } from "react";
import { InfoTip } from "../../components/InfoTip";

const SPAN: Record<1 | 2 | 3, string> = { 1: "", 2: "sm:col-span-2", 3: "sm:col-span-2 xl:col-span-3" };

interface FactCardProps {
  title: string;
  caption?: string;
  hint?: string;
  children: ReactNode;
  span?: 1 | 2 | 3;
  /** Extra grid placement classes. */
  placement?: string;
  /** Shown after the title and info tip. */
  badge?: ReactNode;
}

/** A Fun facts card: title, optional info tip and badge, then the content. */
export function Card({ title, caption, hint, children, span = 1, placement = "", badge }: FactCardProps) {
  return (
    <section className={`min-w-0 rounded-xl border border-slate-800 bg-slate-900 p-3 ${SPAN[span]} ${placement}`}>
      <div className="mb-1.5 flex flex-wrap items-center gap-x-1.5 gap-y-1">
        <h3 className="font-display text-sm text-slate-50">{title}</h3>
        {(caption || hint) && (
          <InfoTip label={`More about ${title}`}>
            {caption && <p>{caption}</p>}
            {hint && <p>{hint}</p>}
          </InfoTip>
        )}
        {badge}
      </div>
      {children}
    </section>
  );
}
