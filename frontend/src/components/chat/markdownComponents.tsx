/**
 * Paylasilmis ReactMarkdown renderer'lari.
 * ChatPanel ve ChatPage tarafindan kullanilir.
 */

import type { Components } from 'react-markdown'

export const markdownComponents: Components = {
  img: ({ src, alt, ...props }: React.ImgHTMLAttributes<HTMLImageElement>) => (
    <img
      src={src}
      alt={alt || ''}
      loading="lazy"
      className="rounded border border-[var(--surface-border)] inline-block object-contain chat-img"
      {...props}
    />
  ),
  a: ({ href, children, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement>) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-[var(--accent-primary)] hover:underline break-words"
      {...props}
    >
      {children}
    </a>
  ),
  table: ({ children, ...props }: React.TableHTMLAttributes<HTMLTableElement>) => (
    <div className="overflow-x-auto my-2 rounded-lg border border-[var(--surface-border)]">
      <table className="min-w-full text-[11px] border-collapse chat-table" {...props}>
        {children}
      </table>
    </div>
  ),
  th: ({ children, ...props }: React.ThHTMLAttributes<HTMLTableCellElement>) => (
    <th
      className="px-2 py-1.5 bg-[var(--surface-raised)] border-b border-[var(--surface-border)] text-left font-semibold text-text-primary whitespace-nowrap text-[11px]"
      {...props}
    >
      {children}
    </th>
  ),
  td: ({ children, ...props }: React.TdHTMLAttributes<HTMLTableCellElement>) => (
    <td
      className="px-2 py-1.5 border-b border-[var(--surface-border)] text-text-primary align-middle text-[11px] max-w-[150px]"
      {...props}
    >
      {children}
    </td>
  ),
  tr: ({ children, ...props }: React.HTMLAttributes<HTMLTableRowElement>) => (
    <tr
      className="hover:bg-[var(--surface-hover)] transition-colors even:bg-[var(--surface-raised)]/40"
      {...props}
    >
      {children}
    </tr>
  ),
}
