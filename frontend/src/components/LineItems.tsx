import { Plus, Trash2 } from "lucide-react";
import type { Product } from "../api/types";
import { money } from "../lib/format";

export interface Line {
  product_id: string;
  quantity: string;
}

/** Editable list of product/quantity lines used by sales and purchase order forms. */
export function LineItems({
  lines,
  onChange,
  products,
  priceOf,
  showStock,
}: {
  lines: Line[];
  onChange: (lines: Line[]) => void;
  products: Product[];
  priceOf: (p: Product) => string;
  showStock?: boolean;
}) {
  const byId = new Map(products.map((p) => [String(p.id), p]));
  const update = (i: number, patch: Partial<Line>) => onChange(lines.map((l, j) => (j === i ? { ...l, ...patch } : l)));
  const total = lines.reduce((sum, l) => {
    const p = byId.get(l.product_id);
    return p ? sum + Number(priceOf(p)) * Number(l.quantity || 0) : sum;
  }, 0);

  return (
    <div className="line-items">
      <table className="table compact">
        <thead>
          <tr><th>Product</th><th style={{ width: 90 }}>Qty</th><th className="right">Unit</th><th className="right">Subtotal</th><th /></tr>
        </thead>
        <tbody>
          {lines.map((l, i) => {
            const p = byId.get(l.product_id);
            const short = showStock && p && Number(l.quantity) > p.quantity;
            return (
              <tr key={i}>
                <td>
                  <select value={l.product_id} onChange={(e) => update(i, { product_id: e.target.value })} required>
                    <option value="">Select a product…</option>
                    {products.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name} ({p.sku}){showStock ? ` · ${p.quantity} in stock` : ""}
                      </option>
                    ))}
                  </select>
                  {short && <div className="field-hint warn">Only {p.quantity} in stock; order can't be confirmed until restocked.</div>}
                </td>
                <td><input type="number" min="1" value={l.quantity} onChange={(e) => update(i, { quantity: e.target.value })} required /></td>
                <td className="right">{p ? money(priceOf(p)) : "—"}</td>
                <td className="right strong">{p ? money(Number(priceOf(p)) * Number(l.quantity || 0)) : "—"}</td>
                <td>
                  <button type="button" className="icon-btn danger" disabled={lines.length === 1}
                    onClick={() => onChange(lines.filter((_, j) => j !== i))} aria-label="Remove line">
                    <Trash2 size={15} />
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <div className="line-items-footer">
        <button type="button" className="btn btn-ghost" onClick={() => onChange([...lines, { product_id: "", quantity: "1" }])}>
          <Plus size={15} /> Add line
        </button>
        <div>Total <strong>{money(total)}</strong></div>
      </div>
    </div>
  );
}
