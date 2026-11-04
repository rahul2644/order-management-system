import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Wand2 } from "lucide-react";
import { api } from "../api/client";
import type { POStatus, PurchaseOrder } from "../api/types";
import { Badge, Empty, ErrorText, Field, Modal, PageHeader, Spinner } from "../components/ui";
import { LineItems, type Line } from "../components/LineItems";
import { useToast } from "../components/Toast";
import { useAllProducts, useSuppliers } from "../lib/hooks";
import { date, dateTime, money } from "../lib/format";

const STATUSES: (POStatus | "")[] = ["", "draft", "ordered", "received", "cancelled"];
const NEXT: Record<POStatus, { status: POStatus; label: string; primary?: boolean }[]> = {
  draft: [{ status: "ordered", label: "Send to supplier", primary: true }, { status: "cancelled", label: "Cancel" }],
  ordered: [{ status: "received", label: "Receive stock", primary: true }, { status: "cancelled", label: "Cancel" }],
  received: [],
  cancelled: [],
};

export function useGenerateFromAlerts() {
  const qc = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: () => api.post<PurchaseOrder[]>("/purchase-orders/from-alerts"),
    onSuccess: (pos) => {
      qc.invalidateQueries({ queryKey: ["purchase-orders"] });
      toast(pos.length ? `Drafted ${pos.length} purchase order${pos.length > 1 ? "s" : ""} from alerts` : "Every low-stock product is already on order");
    },
    onError: (e: Error) => toast(e.message, "error"),
  });
}

export default function PurchaseOrders() {
  const [status, setStatus] = useState<POStatus | "">("");
  const [creating, setCreating] = useState(false);
  const [selected, setSelected] = useState<PurchaseOrder | null>(null);
  const generate = useGenerateFromAlerts();
  const { data, isLoading } = useQuery({
    queryKey: ["purchase-orders", status],
    queryFn: () => api.get<PurchaseOrder[]>("/purchase-orders", { status }),
  });

  return (
    <>
      <PageHeader title="Purchase orders" subtitle="Restock from suppliers. Receiving a PO adds its quantities to stock."
        actions={<>
          <button className="btn" onClick={() => generate.mutate()} disabled={generate.isPending}><Wand2 size={16} /> Draft from alerts</button>
          <button className="btn btn-primary" onClick={() => setCreating(true)}><Plus size={16} /> New PO</button>
        </>} />
      <div className="card">
        <div className="toolbar">
          <div className="segmented">
            {STATUSES.map((s) => (
              <button key={s || "all"} className={status === s ? "active" : ""} onClick={() => setStatus(s)}>
                {s ? s[0].toUpperCase() + s.slice(1) : "All"}
              </button>
            ))}
          </div>
        </div>
        {isLoading ? <Spinner /> : !data?.length ? <Empty message="No purchase orders." /> : (
          <div className="table-wrap">
            <table className="table hover">
              <thead><tr><th>PO</th><th>Supplier</th><th>Lines</th><th>Status</th><th>Expected</th><th>Created</th><th className="right">Total</th></tr></thead>
              <tbody>
                {data.map((po) => (
                  <tr key={po.id} className="clickable" onClick={() => setSelected(po)}>
                    <td className="strong mono">{po.po_number}</td>
                    <td>{po.supplier_name}</td>
                    <td>{po.items.length}</td>
                    <td><Badge value={po.status} /></td>
                    <td>{po.expected_date ? date(po.expected_date) : "—"}</td>
                    <td className="nowrap">{dateTime(po.created_at)}</td>
                    <td className="right strong">{money(po.total)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      {creating && <POForm onClose={() => setCreating(false)} />}
      {selected && <PODetail po={selected} onClose={() => setSelected(null)} onChange={setSelected} />}
    </>
  );
}

function POForm({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const { data: suppliers = [] } = useSuppliers();
  const { data: allProducts = [] } = useAllProducts();
  const [supplierId, setSupplierId] = useState("");
  const [expected, setExpected] = useState("");
  const [notes, setNotes] = useState("");
  const [lines, setLines] = useState<Line[]>([{ product_id: "", quantity: "10" }]);
  const products = supplierId ? allProducts.filter((p) => String(p.supplier_id) === supplierId) : allProducts;

  const save = useMutation({
    mutationFn: () => api.post<PurchaseOrder>("/purchase-orders", {
      supplier_id: Number(supplierId),
      expected_date: expected || null,
      notes: notes || null,
      items: lines.map((l) => ({ product_id: Number(l.product_id), quantity: Number(l.quantity) })),
    }),
    onSuccess: (po) => {
      qc.invalidateQueries({ queryKey: ["purchase-orders"] });
      toast(`${po.po_number} drafted`);
      onClose();
    },
  });

  return (
    <Modal title="New purchase order" onClose={onClose} wide
      footer={<>
        <button className="btn" onClick={onClose}>Cancel</button>
        <button className="btn btn-primary" form="po-form" disabled={save.isPending}>Create draft</button>
      </>}>
      <form id="po-form" onSubmit={(e: FormEvent) => { e.preventDefault(); save.mutate(); }}>
        <div className="form-grid">
          <Field label="Supplier">
            <select value={supplierId} onChange={(e) => { setSupplierId(e.target.value); setLines([{ product_id: "", quantity: "10" }]); }} required>
              <option value="">Select a supplier…</option>
              {suppliers.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </Field>
          <Field label="Expected delivery"><input type="date" value={expected} onChange={(e) => setExpected(e.target.value)} /></Field>
        </div>
        <LineItems lines={lines} onChange={setLines} products={products} priceOf={(p) => p.cost_price} />
        <Field label="Notes"><textarea rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} /></Field>
        <ErrorText error={save.error} />
      </form>
    </Modal>
  );
}

function PODetail({ po, onClose, onChange }: { po: PurchaseOrder; onClose: () => void; onChange: (p: PurchaseOrder) => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const update = useMutation({
    mutationFn: (status: POStatus) => api.patch<PurchaseOrder>(`/purchase-orders/${po.id}/status`, { status }),
    onSuccess: (p) => {
      ["purchase-orders", "products", "dashboard", "alerts", "movements"].forEach((k) => qc.invalidateQueries({ queryKey: [k] }));
      toast(p.status === "received" ? `${p.po_number} received; stock updated` : `${p.po_number} is now ${p.status}`);
      onChange(p);
    },
  });
  return (
    <Modal title={`Purchase order ${po.po_number}`} onClose={onClose} wide
      footer={NEXT[po.status].length ? NEXT[po.status].map((a) => (
        <button key={a.status} className={`btn ${a.primary ? "btn-primary" : "btn-danger-ghost"}`} disabled={update.isPending}
          onClick={() => update.mutate(a.status)}>{a.label}</button>
      )) : undefined}>
      <div className="detail-grid">
        <div><span className="muted small">Supplier</span><div className="strong">{po.supplier_name}</div></div>
        <div><span className="muted small">Status</span><div><Badge value={po.status} /></div></div>
        <div><span className="muted small">Expected</span><div>{po.expected_date ? date(po.expected_date) : "—"}</div></div>
        <div><span className="muted small">Received</span><div>{po.received_at ? dateTime(po.received_at) : "—"}</div></div>
      </div>
      <table className="table compact">
        <thead><tr><th>Product</th><th className="right">Qty</th><th className="right">Unit cost</th><th className="right">Subtotal</th></tr></thead>
        <tbody>
          {po.items.map((i) => (
            <tr key={i.id}>
              <td><div className="strong">{i.product_name}</div><div className="muted small mono">{i.product_sku}</div></td>
              <td className="right">{i.quantity}</td>
              <td className="right">{money(i.unit_cost)}</td>
              <td className="right">{money(Number(i.unit_cost) * i.quantity)}</td>
            </tr>
          ))}
          <tr className="total-row"><td colSpan={3} className="right">Total</td><td className="right">{money(po.total)}</td></tr>
        </tbody>
      </table>
      {po.notes && <p className="muted">{po.notes}</p>}
      <ErrorText error={update.error} />
    </Modal>
  );
}
