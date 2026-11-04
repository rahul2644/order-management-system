import { useState, type FormEvent } from "react";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Search } from "lucide-react";
import { api } from "../api/client";
import type { Order, OrderStatus, Page } from "../api/types";
import { Badge, Empty, ErrorText, Field, Modal, PageHeader, Pagination, Spinner } from "../components/ui";
import { LineItems, type Line } from "../components/LineItems";
import { useToast } from "../components/Toast";
import { useAllProducts, useDebounced } from "../lib/hooks";
import { dateTime, money } from "../lib/format";

const STATUSES: (OrderStatus | "")[] = ["", "pending", "confirmed", "shipped", "delivered", "cancelled"];

const NEXT_ACTIONS: Record<OrderStatus, { status: OrderStatus; label: string; primary?: boolean }[]> = {
  pending: [{ status: "confirmed", label: "Confirm & reserve stock", primary: true }, { status: "cancelled", label: "Cancel order" }],
  confirmed: [{ status: "shipped", label: "Mark shipped", primary: true }, { status: "cancelled", label: "Cancel & restock" }],
  shipped: [{ status: "delivered", label: "Mark delivered", primary: true }],
  delivered: [],
  cancelled: [],
};

export default function Orders() {
  const [status, setStatus] = useState<OrderStatus | "">("");
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [creating, setCreating] = useState(false);
  const [selected, setSelected] = useState<Order | null>(null);
  const search = useDebounced(q);

  const { data, isLoading } = useQuery({
    queryKey: ["orders", { status, search, page }],
    queryFn: () => api.get<Page<Order>>("/orders", { status, q: search, page, size: 15 }),
    placeholderData: keepPreviousData,
  });

  return (
    <>
      <PageHeader title="Sales orders" subtitle="Customer orders from placement through delivery."
        actions={<button className="btn btn-primary" onClick={() => setCreating(true)}><Plus size={16} /> New order</button>} />
      <div className="card">
        <div className="toolbar">
          <div className="search">
            <Search size={16} />
            <input placeholder="Order # or customer…" value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} />
          </div>
          <div className="segmented">
            {STATUSES.map((s) => (
              <button key={s || "all"} className={status === s ? "active" : ""} onClick={() => { setStatus(s); setPage(1); }}>
                {s ? s[0].toUpperCase() + s.slice(1) : "All"}
              </button>
            ))}
          </div>
        </div>
        {isLoading ? <Spinner /> : !data?.items.length ? <Empty message="No orders found." /> : (
          <div className="table-wrap">
            <table className="table hover">
              <thead><tr><th>Order</th><th>Customer</th><th>Items</th><th>Status</th><th>Placed</th><th className="right">Total</th></tr></thead>
              <tbody>
                {data.items.map((o) => (
                  <tr key={o.id} onClick={() => setSelected(o)} className="clickable">
                    <td className="strong mono">{o.order_number}</td>
                    <td>
                      <div>{o.customer_name}</div>
                      <div className="muted small">{o.customer_email}</div>
                    </td>
                    <td>{o.items.reduce((n, i) => n + i.quantity, 0)} units</td>
                    <td><Badge value={o.status} /></td>
                    <td className="nowrap">{dateTime(o.created_at)}</td>
                    <td className="right strong">{money(o.total)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {data && <Pagination page={page} size={data.size} total={data.total} onChange={setPage} />}
      </div>
      {creating && <OrderForm onClose={() => setCreating(false)} />}
      {selected && <OrderDetail order={selected} onClose={() => setSelected(null)} onChange={setSelected} />}
    </>
  );
}

function OrderForm({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const { data: products = [] } = useAllProducts();
  const [customer, setCustomer] = useState({ name: "", email: "", notes: "" });
  const [lines, setLines] = useState<Line[]>([{ product_id: "", quantity: "1" }]);

  const save = useMutation({
    mutationFn: () => api.post<Order>("/orders", {
      customer_name: customer.name,
      customer_email: customer.email || null,
      notes: customer.notes || null,
      items: lines.map((l) => ({ product_id: Number(l.product_id), quantity: Number(l.quantity) })),
    }),
    onSuccess: (o) => {
      qc.invalidateQueries({ queryKey: ["orders"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      toast(`Order ${o.order_number} created`);
      onClose();
    },
  });

  return (
    <Modal title="New sales order" onClose={onClose} wide
      footer={<>
        <button className="btn" onClick={onClose}>Cancel</button>
        <button className="btn btn-primary" form="order-form" disabled={save.isPending}>Create order</button>
      </>}>
      <form id="order-form" onSubmit={(e: FormEvent) => { e.preventDefault(); save.mutate(); }}>
        <div className="form-grid">
          <Field label="Customer name"><input value={customer.name} onChange={(e) => setCustomer({ ...customer, name: e.target.value })} required /></Field>
          <Field label="Customer email"><input type="email" value={customer.email} onChange={(e) => setCustomer({ ...customer, email: e.target.value })} /></Field>
        </div>
        <LineItems lines={lines} onChange={setLines} products={products} priceOf={(p) => p.unit_price} showStock />
        <Field label="Notes"><textarea rows={2} value={customer.notes} onChange={(e) => setCustomer({ ...customer, notes: e.target.value })} /></Field>
        <ErrorText error={save.error} />
      </form>
    </Modal>
  );
}

function OrderDetail({ order, onClose, onChange }: { order: Order; onClose: () => void; onChange: (o: Order) => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const update = useMutation({
    mutationFn: (status: OrderStatus) => api.patch<Order>(`/orders/${order.id}/status`, { status }),
    onSuccess: (o) => {
      ["orders", "products", "dashboard", "alerts", "movements"].forEach((k) => qc.invalidateQueries({ queryKey: [k] }));
      toast(`${o.order_number} is now ${o.status}`);
      onChange(o);
    },
  });

  return (
    <Modal title={`Order ${order.order_number}`} onClose={onClose} wide
      footer={NEXT_ACTIONS[order.status].length ? (
        <>
          {NEXT_ACTIONS[order.status].map((a) => (
            <button key={a.status} className={`btn ${a.primary ? "btn-primary" : "btn-danger-ghost"}`}
              disabled={update.isPending} onClick={() => update.mutate(a.status)}>
              {a.label}
            </button>
          ))}
        </>
      ) : undefined}>
      <div className="detail-grid">
        <div><span className="muted small">Customer</span><div className="strong">{order.customer_name}</div><div className="muted small">{order.customer_email}</div></div>
        <div><span className="muted small">Status</span><div><Badge value={order.status} /></div></div>
        <div><span className="muted small">Placed</span><div>{dateTime(order.created_at)}</div></div>
        <div><span className="muted small">Confirmed</span><div>{order.confirmed_at ? dateTime(order.confirmed_at) : "—"}</div></div>
      </div>
      <OrderTimeline status={order.status} />
      <table className="table compact">
        <thead><tr><th>Product</th><th className="right">Qty</th><th className="right">Unit price</th><th className="right">Subtotal</th></tr></thead>
        <tbody>
          {order.items.map((i) => (
            <tr key={i.id}>
              <td><div className="strong">{i.product_name}</div><div className="muted small mono">{i.product_sku}</div></td>
              <td className="right">{i.quantity}</td>
              <td className="right">{money(i.unit_price)}</td>
              <td className="right">{money(Number(i.unit_price) * i.quantity)}</td>
            </tr>
          ))}
          <tr className="total-row"><td colSpan={3} className="right">Total</td><td className="right">{money(order.total)}</td></tr>
        </tbody>
      </table>
      {order.notes && <p className="muted">{order.notes}</p>}
      <ErrorText error={update.error} />
    </Modal>
  );
}

function OrderTimeline({ status }: { status: OrderStatus }) {
  const steps: OrderStatus[] = ["pending", "confirmed", "shipped", "delivered"];
  if (status === "cancelled") return <div className="timeline cancelled">This order was cancelled.</div>;
  const idx = steps.indexOf(status);
  return (
    <ol className="timeline">
      {steps.map((s, i) => (
        <li key={s} className={i <= idx ? "done" : ""}><span className="dot" />{s}</li>
      ))}
    </ol>
  );
}
