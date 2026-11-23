export interface DescriptionLine {
  bold?: string;
  text: string;
}

export function Description({ lines }: { lines: DescriptionLine[] }) {
  return (
    <div className="space-y-0.5 text-xs text-slate-400">
      {lines.map((line, i) => (
        <p key={i}>
          {line.bold && <strong className="text-slate-200">{line.bold}</strong>}
          {line.text}
        </p>
      ))}
    </div>
  );
}
