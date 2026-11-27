import { Fragment } from "react";

/** Renders line breaks and **bold** segments of a plain string. */
export function RichText({ text }: { text: string }) {
  return (
    <span className="whitespace-pre-line">
      {text.split("**").map((part, i) =>
        i % 2 === 1 ? (
          <strong key={i} className="font-semibold text-slate-50">
            {part}
          </strong>
        ) : (
          <Fragment key={i}>{part}</Fragment>
        ),
      )}
    </span>
  );
}
