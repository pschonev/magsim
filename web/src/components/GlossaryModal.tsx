import { BookOpen, GitFork, Search, X, Zap } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";
import { TWIST_DESCRIPTIONS } from "../features/dashboard/charts/twistCards";
import { displayName } from "../utils/names";
import { readableText } from "../utils/palette";
import { RACER_GLOSSARY, type RacerGlossaryEntry } from "../utils/racerGlossary";
import { useTheme } from "../utils/ThemeProvider";

type SectionId = "base" | "second" | "twist";

interface Section {
  id: SectionId;
  label: string;
  heading: string;
}

interface GlossaryItem {
  section: SectionId;
  key: string;
  name: string;
  nameKey: string;
  title: string | null;
  ability: string;
  abilityKey: string;
  clarifications: string | null;
  implemented: boolean;
  decision: boolean;
  hasColor: boolean;
  showMarker: boolean;
}

const AUTOMATIC_LABEL = "Automatic: the power always applies, no choices";
const DECISION_LABEL = "Has a decision: the player chooses when or how to use the power";

const SECTIONS: Section[] = [
  { id: "base", label: "Base game", heading: "Base game racers" },
  { id: "second", label: "Second Wind", heading: "Second Wind racers" },
  { id: "twist", label: "Twist cards", heading: "Twist cards" },
];

/** Lower case without accents, so "pinata" finds Piñata. */
const fold = (text: string): string =>
  text
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase();

/** Name key without spaces and punctuation, so "rerunner" finds Re-Runner and "mr dice" finds Mr. Dice Guy. */
const nameKeyOf = (name: string): string => fold(name).replace(/[^a-z0-9]/g, "");

function racerItem(entry: RacerGlossaryEntry): GlossaryItem {
  const name = displayName(entry.key);
  return {
    section: entry.set === "Base game" ? "base" : "second",
    key: entry.key,
    name,
    nameKey: nameKeyOf(name),
    title: entry.title,
    ability: entry.ability,
    abilityKey: fold(entry.ability),
    clarifications: entry.clarifications,
    implemented: entry.implemented,
    decision: entry.decision,
    hasColor: true,
    showMarker: entry.implemented,
  };
}

function twistItem([key, description]: [string, string]): GlossaryItem {
  const name = displayName(key);
  return {
    section: "twist",
    key,
    name,
    nameKey: nameKeyOf(name),
    title: null,
    ability: description,
    abilityKey: fold(description),
    clarifications: null,
    implemented: true,
    decision: false,
    hasColor: false,
    showMarker: false,
  };
}

const byName = (a: GlossaryItem, b: GlossaryItem) => a.name.localeCompare(b.name);

const ITEMS: GlossaryItem[] = [
  ...RACER_GLOSSARY.map(racerItem),
  ...Object.entries(TWIST_DESCRIPTIONS).map(twistItem),
].sort(byName);

function matches(item: GlossaryItem, query: string): boolean {
  const text = fold(query.trim());
  if (!text) return true;
  const key = nameKeyOf(text);
  return (key !== "" && item.nameKey.includes(key)) || item.abilityKey.includes(text);
}

function PowerMarker({ decision }: { decision: boolean }) {
  const label = decision ? DECISION_LABEL : AUTOMATIC_LABEL;
  const Icon = decision ? GitFork : Zap;
  return (
    <span title={label} aria-label={label} role="img" className="inline-flex text-slate-400">
      <Icon className="h-3 w-3" aria-hidden="true" />
    </span>
  );
}

function ItemCard({ item, color }: { item: GlossaryItem; color: string | undefined }) {
  return (
    <article className="rounded-lg border border-slate-800 p-3">
      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
        <h4 className={`text-sm font-bold ${color ? "" : "text-slate-50"}`} style={color ? { color } : undefined}>
          {item.name}
        </h4>
        {item.showMarker && <PowerMarker decision={item.decision} />}
        {item.title && (
          <span className="text-[10px] font-semibold tracking-wider text-slate-400 uppercase">{item.title}</span>
        )}
        {!item.implemented && (
          <span className="rounded border border-slate-700 px-1 text-[10px] text-slate-400">not simulated</span>
        )}
      </div>
      <p className="mt-1 text-xs text-slate-200">{item.ability}</p>
      {item.clarifications && (
        <p className="mt-1.5 text-[11px] text-slate-400">
          <span className="font-semibold">Clarifications:</span> {item.clarifications}
        </p>
      )}
    </article>
  );
}

function GlossaryDialog({ onClose, racerColors }: { onClose: () => void; racerColors: Record<string, string> }) {
  const { chart: theme } = useTheme();
  const titleId = useId();
  const [query, setQuery] = useState("");
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const sectionRefs = useRef<Partial<Record<SectionId, HTMLElement | null>>>({});

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    document.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", onKey);
    };
  }, [onClose]);

  const found = ITEMS.filter((item) => matches(item, query));
  const searching = query.trim() !== "";
  const countIn = (items: GlossaryItem[], id: SectionId) => items.filter((i) => i.section === id).length;

  const jumpTo = (id: SectionId) => {
    const target = sectionRefs.current[id];
    if (!target) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    scrollRef.current?.scrollTo({ top: target.offsetTop, behavior: reduced ? "auto" : "smooth" });
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-2 backdrop-blur-sm sm:p-6"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="flex h-full w-full max-w-5xl flex-col overflow-hidden rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl"
      >
        <div className="shrink-0 space-y-2 border-b border-slate-800 bg-slate-900 p-3 sm:p-4">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <BookOpen className="h-4 w-4 text-indigo-400" />
              <h2 id={titleId} className="text-base font-semibold text-slate-50">
                Glossary
              </h2>
            </div>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close glossary"
              className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-lg text-slate-400 hover:bg-slate-800 hover:text-slate-50 sm:h-8 sm:w-8 pointer-coarse:h-10 pointer-coarse:w-10"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <label className="relative min-w-48 flex-1">
              <span className="sr-only">Search racers and twist cards</span>
              <Search className="pointer-events-none absolute top-1/2 left-2.5 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
              <input
                type="search"
                autoFocus={!window.matchMedia("(pointer: coarse)").matches}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search by name or ability text"
                className="w-full rounded-lg border border-slate-700 bg-slate-950 py-1.5 pr-3 pl-8 text-xs text-slate-200 placeholder-slate-500 focus:border-indigo-500 focus:outline-none max-sm:min-h-10 pointer-coarse:min-h-10"
              />
            </label>
            <div className="flex flex-wrap items-center gap-1.5">
              {SECTIONS.map((section) => {
                const total = countIn(ITEMS, section.id);
                const hits = countIn(found, section.id);
                return (
                  <button
                    key={section.id}
                    type="button"
                    disabled={hits === 0}
                    onClick={() => jumpTo(section.id)}
                    className="rounded-full border border-slate-700 bg-slate-950 px-3 py-1 text-xs text-slate-200 hover:border-indigo-500 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:border-slate-700 max-sm:min-h-9 pointer-coarse:min-h-9"
                  >
                    {section.label}{" "}
                    <span className="text-slate-400">{searching ? `${hits}/${total}` : total}</span>
                  </button>
                );
              })}
            </div>
          </div>
          <p className="flex flex-wrap items-center gap-x-4 gap-y-0.5 text-[11px] text-slate-400">
            <span className="inline-flex items-center gap-1">
              <Zap className="h-3 w-3" aria-hidden="true" /> Automatic: the power always applies, no choices
            </span>
            <span className="inline-flex items-center gap-1">
              <GitFork className="h-3 w-3" aria-hidden="true" /> Decision: the player chooses when or how to use the
              power
            </span>
          </p>
        </div>

        <div ref={scrollRef} className="relative min-h-0 flex-1 space-y-6 overflow-y-auto p-3 sm:p-4">
          {found.length === 0 && <p className="py-10 text-center text-sm text-slate-400">No matches</p>}
          {SECTIONS.map((section) => {
            const items = found.filter((item) => item.section === section.id);
            if (items.length === 0) return null;
            return (
              <section
                key={section.id}
                ref={(el) => {
                  sectionRefs.current[section.id] = el;
                }}
                aria-label={section.heading}
              >
                <h3 className="mb-2 text-xs font-semibold tracking-wider text-slate-400 uppercase">
                  {section.heading} ({items.length})
                </h3>
                <div className="grid gap-2 sm:grid-cols-2">
                  {items.map((item) => {
                    const base = racerColors[item.key];
                    const color = item.hasColor && base ? readableText(base, theme.tooltipBg) : undefined;
                    return <ItemCard key={`${item.section}-${item.key}`} item={item} color={color} />;
                  })}
                </div>
              </section>
            );
          })}
        </div>
      </div>
    </div>
  );
}

interface GlossaryModalProps {
  open: boolean;
  onClose: () => void;
  racerColors: Record<string, string>;
}

/** Full-screen glossary of all racer cards and twist cards, searchable, with jumps to each section. */
export function GlossaryModal({ open, onClose, racerColors }: GlossaryModalProps) {
  if (!open) return null;
  return <GlossaryDialog onClose={onClose} racerColors={racerColors} />;
}
