import { useEffect, type ReactNode } from "react";
import { X, ChevronLeft, ChevronRight, Inbox } from "lucide-react";

export function Modal({
  title,
  onClose,
  children,
  footer,
  wide,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
  wide?: boolean;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="modal-backdrop" onMouseDown={onClose}>
      <div className={`modal ${wide ? "modal-wide" : ""}`} onMouseDown={(e) => e.stopPropagation()} role="dialog" aria-label={title}>
        <header className="modal-header">
          <h2>{title}</h2>
          <button className="icon-btn" onClick={onClose} aria-label="Close">
            <X size={18} />
          </button>
        </header>
        <div className="modal-body">{children}</div>
        {footer && <footer className="modal-footer">{footer}</footer>}
      </div>
    </div>
  );
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <div className="page-header">
      <div>
        <h1>{title}</h1>
        {subtitle && <p className="muted">{subtitle}</p>}
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </div>
  );
}

const BADGE_TONES: Record<string, string> = {
  pending: "amber",
  draft: "gray",
  confirmed: "blue",
  ordered: "blue",
  shipped: "violet",
  delivered: "green",
  received: "green",
  cancelled: "red",
  open: "red",
  resolved: "green",
  purchase: "green",
  sale: "blue",
  adjustment: "gray",
  return: "amber",
  admin: "violet",
  staff: "gray",
};

export function Badge({ value, tone }: { value: string; tone?: string }) {
  return <span className={`badge badge-${tone ?? BADGE_TONES[value] ?? "gray"}`}>{value}</span>;
}

export function StockPill({ quantity, reorderLevel }: { quantity: number; reorderLevel: number }) {
  const tone = quantity === 0 ? "red" : quantity <= reorderLevel ? "amber" : "green";
  const label = quantity === 0 ? "Out of stock" : quantity <= reorderLevel ? "Low" : "In stock";
  return (
    <span className={`stock-pill stock-${tone}`} title={`Reorder level: ${reorderLevel}`}>
      <span className="dot" />
      <strong>{quantity}</strong> <span className="muted">· {label}</span>
    </span>
  );
}

export function Pagination({ page, size, total, onChange }: { page: number; size: number; total: number; onChange: (p: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / size));
  const from = total === 0 ? 0 : (page - 1) * size + 1;
  return (
    <div className="pagination">
      <span className="muted">
        {from}–{Math.min(page * size, total)} of {total}
      </span>
      <div className="pagination-buttons">
        <button className="icon-btn" disabled={page <= 1} onClick={() => onChange(page - 1)} aria-label="Previous page">
          <ChevronLeft size={16} />
        </button>
        <span>
          {page} / {pages}
        </span>
        <button className="icon-btn" disabled={page >= pages} onClick={() => onChange(page + 1)} aria-label="Next page">
          <ChevronRight size={16} />
        </button>
      </div>
    </div>
  );
}

export function Empty({ message, children }: { message: string; children?: ReactNode }) {
  return (
    <div className="empty">
      <Inbox size={28} />
      <p>{message}</p>
      {children}
    </div>
  );
}

export function Spinner() {
  return <div className="spinner" aria-label="Loading" />;
}

export function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: string }) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      {children}
      {hint && <span className="field-hint">{hint}</span>}
    </label>
  );
}

export function ErrorText({ error }: { error: unknown }) {
  if (!error) return null;
  return <div className="form-error">{error instanceof Error ? error.message : String(error)}</div>;
}
