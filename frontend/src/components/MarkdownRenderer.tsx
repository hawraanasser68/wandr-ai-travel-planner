import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function MarkdownRenderer({ content }: { content: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        h1: ({ children }) => <h1 className="text-lg font-bold mt-4 mb-2 text-slate-900">{children}</h1>,
        h2: ({ children }) => <h2 className="text-base font-bold mt-3 mb-1.5 text-slate-800">{children}</h2>,
        h3: ({ children }) => <h3 className="text-sm font-semibold mt-3 mb-1 text-slate-800">{children}</h3>,
        p:  ({ children }) => <p className="mb-2 leading-relaxed text-slate-700">{children}</p>,
        ul: ({ children }) => <ul className="list-disc pl-5 mb-2 space-y-1 text-slate-700">{children}</ul>,
        ol: ({ children }) => <ol className="list-decimal pl-5 mb-2 space-y-1 text-slate-700">{children}</ol>,
        li: ({ children }) => <li className="leading-relaxed">{children}</li>,
        strong: ({ children }) => <strong className="font-semibold text-slate-900">{children}</strong>,
        em: ({ children }) => <em className="italic text-slate-600">{children}</em>,
        code: ({ children }) => (
          <code className="rounded px-1.5 py-0.5 text-xs font-mono"
                style={{ background: "#f1f5f9", color: "#334155" }}>{children}</code>
        ),
        blockquote: ({ children }) => (
          <blockquote className="pl-4 italic my-2"
                      style={{ borderLeft: "3px solid #6366f1", color: "#64748b" }}>{children}</blockquote>
        ),
        hr: () => <hr className="my-3" style={{ borderColor: "#e2e8f0" }} />,
        table: ({ children }) => (
          <div className="overflow-x-auto my-2">
            <table className="text-xs w-full" style={{ borderCollapse: "collapse" }}>{children}</table>
          </div>
        ),
        th: ({ children }) => (
          <th className="px-3 py-2 text-left text-xs font-semibold text-slate-600"
              style={{ background: "#f8fafc", border: "1px solid #e2e8f0" }}>{children}</th>
        ),
        td: ({ children }) => (
          <td className="px-3 py-2 text-xs text-slate-700"
              style={{ border: "1px solid #e2e8f0" }}>{children}</td>
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  );
}
