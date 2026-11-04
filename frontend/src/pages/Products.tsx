import { useState, type FormEvent } from "react";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Search, Pencil, Trash2, ArrowUpDown, History, PackagePlus } from "lucide-react";
import { api } from "../api/client";
import type { Page, Product, StockMovement, MovementType } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { Badge, Empty, ErrorText, Field, Modal, PageHeader, Pagination, Spinner, StockPill } from "../components/ui";
import { useToast } from "../components/Toast";
import { useCategories, useDebounced, useSuppliers } from "../lib/hooks";
import { dateTime, money } from "../lib/format";

type Sort = "name" | "sku" | "quantity" | "unit_price" | "updated_at";

export default function Products() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const toast = useToast();
  const [q, setQ] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [supplierId, setSupplierId] = useState("");
  const [lowStock, setLowStock] = useState(false);
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState<{ by: Sort; order: "asc" | "desc" }>({ by: "name", order: "asc" });
  const [editing, setEditing] = useState<Product | "new" | null>(null);
  const [adjusting, setAdjusting] = useState<Product | null>(null);
  const [history, setHistory] = useState<Product | null>(null);
  const search = useDebounced(q);

  const { data: categories } = useCategories();
  const { data: suppliers } = useSuppliers();
  const { data, isLoading } = useQuery({
    queryKey: ["products", { search, categoryId, supplierId, lowStock, page, sort }],
    queryFn: () =>
      api.get<Page<Product>>("/products", {
        q: search, category_id: categoryId, supplier_id: supplierId, low_stock: lowStock || undefined,
        page, size: 15, sort: sort.by, order: sort.order,
      }),
    placeholderData: keepPreviousData,
  });

  const remove = useMutation({
    mutationFn: (id: number) => api.delete(`/products/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["products"] });
      toast("Product removed");
    },
    onError: (e: Error) => toast(e.message, "error"),
  });

  const toggleSort = (by: Sort) =>
    setSort((s) => ({ by, order: s.by === by && s.order === "asc" ? "desc" : "asc" }));

  const SortTh = ({ by, children, right }: { by: Sort; children: string; right?: boolean }) => (
    <th className={`sortable ${right ? "right" : ""}`} onClick={() => toggleSort(by)}>
      {children} <ArrowUpDown size={12} className={sort.by === by ? "active" : ""} />
    </th>
  );

  return (
    <>
      <PageHeader
        title="Products"
        subtitle="Your catalog, pricing and on-hand stock."
        actions={
          <button className="btn btn-primary" onClick={() => setEditing("new")}>
            <Plus size={16} /> Add product
          </button>
        }
      />

      <div className="card">
        <div className="toolbar">
          <div className="search">
            <Search size={16} />
            <input placeholder="Search by name or SKU…" value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} />
          </div>
          <select value={categoryId} onChange={(e) => { setCategoryId(e.target.value); setPage(1); }}>
            <option value="">All categories</option>
            {categories?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
          <select value={supplierId} onChange={(e) => { setSupplierId(e.target.value); setPage(1); }}>
            <option value="">All suppliers</option>
            {suppliers?.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
          <label className="checkbox">
            <input type="checkbox" checked={lowStock} onChange={(e) => { setLowStock(e.target.checked); setPage(1); }} />
            Low stock only
          </label>
        </div>

        {isLoading ? <Spinner /> : !data?.items.length ? (
          <Empty message="No products match your filters." />
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <SortTh by="name">Product</SortTh>
                  <SortTh by="sku">SKU</SortTh>
                  <th>Category</th>
                  <th>Supplier</th>
                  <SortTh by="unit_price" right>Price</SortTh>
                  <th className="right">Margin</th>
                  <SortTh by="quantity">Stock</SortTh>
                  <th />
                </tr>
              </thead>
              <tbody>
                {data.items.map((p) => {
                  const margin = Number(p.unit_price) ? ((Number(p.unit_price) - Number(p.cost_price)) / Number(p.unit_price)) * 100 : 0;
                  return (
                    <tr key={p.id}>
                      <td className="strong">{p.name}</td>
                      <td className="mono">{p.sku}</td>
                      <td>{p.category ? <Badge value={p.category.name} tone="gray" /> : "—"}</td>
                      <td>{p.supplier_name ?? "—"}</td>
                      <td className="right">{money(p.unit_price)}</td>
                      <td className="right muted">{margin.toFixed(0)}%</td>
                      <td><StockPill quantity={p.quantity} reorderLevel={p.reorder_level} /></td>
                      <td className="row-actions">
                        <button className="icon-btn" title="Adjust stock" onClick={() => setAdjusting(p)}><PackagePlus size={16} /></button>
                        <button className="icon-btn" title="Stock history" onClick={() => setHistory(p)}><History size={16} /></button>
                        <button className="icon-btn" title="Edit" onClick={() => setEditing(p)}><Pencil size={16} /></button>
                        {user?.role === "admin" && (
                          <button className="icon-btn danger" title="Delete"
                            onClick={() => window.confirm(`Delete ${p.name}?`) && remove.mutate(p.id)}>
                            <Trash2 size={16} />
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        {data && <Pagination page={page} size={data.size} total={data.total} onChange={setPage} />}
      </div>

      {editing && <ProductForm product={editing === "new" ? null : editing} onClose={() => setEditing(null)} />}
      {adjusting && <AdjustStock product={adjusting} onClose={() => setAdjusting(null)} />}
      {history && <StockHistory product={history} onClose={() => setHistory(null)} />}
    </>
  );
}

function ProductForm({ product, onClose }: { product: Product | null; onClose: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const { data: categories } = useCategories();
  const { data: suppliers } = useSuppliers();
  const [form, setForm] = useState({
    sku: product?.sku ?? "",
    name: product?.name ?? "",
    description: product?.description ?? "",
    category_id: product?.category_id?.toString() ?? "",
    supplier_id: product?.supplier_id?.toString() ?? "",
    unit_price: product?.unit_price ?? "",
    cost_price: product?.cost_price ?? "",
    quantity: "0",
    reorder_level: product?.reorder_level.toString() ?? "10",
    reorder_quantity: product?.reorder_quantity.toString() ?? "50",
  });
  const set = (k: keyof typeof form) => (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value });

  const save = useMutation({
    mutationFn: () => {
      const body = {
        ...form,
        description: form.description || null,
        category_id: form.category_id ? Number(form.category_id) : null,
        supplier_id: form.supplier_id ? Number(form.supplier_id) : null,
        reorder_level: Number(form.reorder_level),
        reorder_quantity: Number(form.reorder_quantity),
        quantity: product ? undefined : Number(form.quantity),
      };
      return product ? api.patch(`/products/${product.id}`, body) : api.post("/products", body);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["products"] });
      qc.invalidateQueries({ queryKey: ["alerts"] });
      toast(product ? "Product updated" : "Product created");
      onClose();
    },
  });

  const submit = (e: FormEvent) => { e.preventDefault(); save.mutate(); };

  return (
    <Modal title={product ? `Edit ${product.name}` : "New product"} onClose={onClose} wide
      footer={<>
        <button className="btn" onClick={onClose}>Cancel</button>
        <button className="btn btn-primary" form="product-form" disabled={save.isPending}>Save</button>
      </>}>
      <form id="product-form" className="form-grid" onSubmit={submit}>
        <Field label="Name"><input value={form.name} onChange={set("name")} required /></Field>
        <Field label="SKU"><input value={form.sku} onChange={set("sku")} required /></Field>
        <Field label="Category">
          <select value={form.category_id} onChange={set("category_id")}>
            <option value="">—</option>
            {categories?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </Field>
        <Field label="Supplier">
          <select value={form.supplier_id} onChange={set("supplier_id")}>
            <option value="">—</option>
            {suppliers?.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </Field>
        <Field label="Unit price ($)"><input type="number" step="0.01" min="0" value={form.unit_price} onChange={set("unit_price")} required /></Field>
        <Field label="Cost price ($)"><input type="number" step="0.01" min="0" value={form.cost_price} onChange={set("cost_price")} required /></Field>
        <Field label="Reorder level" hint="An alert is raised when stock falls to this level.">
          <input type="number" min="0" value={form.reorder_level} onChange={set("reorder_level")} required />
        </Field>
        <Field label="Reorder quantity" hint="Default quantity for auto-generated purchase orders.">
          <input type="number" min="1" value={form.reorder_quantity} onChange={set("reorder_quantity")} required />
        </Field>
        {!product && (
          <Field label="Opening stock"><input type="number" min="0" value={form.quantity} onChange={set("quantity")} /></Field>
        )}
        <div className="span-2">
          <Field label="Description"><textarea rows={3} value={form.description} onChange={set("description")} /></Field>
        </div>
        <div className="span-2"><ErrorText error={save.error} /></div>
      </form>
    </Modal>
  );
}

function AdjustStock({ product, onClose }: { product: Product; onClose: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [direction, setDirection] = useState<"in" | "out">("in");
  const [amount, setAmount] = useState("1");
  const [type, setType] = useState<MovementType>("adjustment");
  const [note, setNote] = useState("");
  const change = (direction === "in" ? 1 : -1) * Number(amount || 0);

  const save = useMutation({
    mutationFn: () => api.post<Product>(`/products/${product.id}/stock`, { change, movement_type: type, note: note || null }),
    onSuccess: (p) => {
      qc.invalidateQueries({ queryKey: ["products"] });
      qc.invalidateQueries({ queryKey: ["alerts"] });
      qc.invalidateQueries({ queryKey: ["movements"] });
      toast(`${p.name}: stock is now ${p.quantity}`);
      onClose();
    },
  });

  return (
    <Modal title={`Adjust stock · ${product.name}`} onClose={onClose}
      footer={<>
        <button className="btn" onClick={onClose}>Cancel</button>
        <button className="btn btn-primary" disabled={!change || save.isPending} onClick={() => save.mutate()}>Apply</button>
      </>}>
      <div className="segmented">
        <button className={direction === "in" ? "active" : ""} onClick={() => setDirection("in")}>Add stock</button>
        <button className={direction === "out" ? "active" : ""} onClick={() => setDirection("out")}>Remove stock</button>
      </div>
      <div className="form-grid">
        <Field label="Quantity"><input type="number" min="1" value={amount} onChange={(e) => setAmount(e.target.value)} /></Field>
        <Field label="Reason">
          <select value={type} onChange={(e) => setType(e.target.value as MovementType)}>
            <option value="adjustment">Adjustment / count</option>
            <option value="purchase">Received from supplier</option>
            <option value="return">Customer return</option>
            <option value="sale">Manual sale</option>
          </select>
        </Field>
        <div className="span-2"><Field label="Note"><input value={note} onChange={(e) => setNote(e.target.value)} placeholder="e.g. Cycle count, damaged in transit" /></Field></div>
      </div>
      <p className="muted small">
        Current: <strong>{product.quantity}</strong> → After: <strong>{product.quantity + change}</strong>
      </p>
      <ErrorText error={save.error} />
    </Modal>
  );
}

function StockHistory({ product, onClose }: { product: Product; onClose: () => void }) {
  const { data, isLoading } = useQuery({
    queryKey: ["movements", product.id],
    queryFn: () => api.get<StockMovement[]>(`/products/${product.id}/movements`, { limit: 100 }),
  });
  return (
    <Modal title={`Stock history · ${product.name}`} onClose={onClose} wide>
      {isLoading ? <Spinner /> : (
        <div className="table-wrap scroll-y">
          <table className="table">
            <thead><tr><th>When</th><th>Type</th><th className="right">Change</th><th className="right">Balance</th><th>Reference</th></tr></thead>
            <tbody>
              {data?.map((m) => (
                <tr key={m.id}>
                  <td>{dateTime(m.created_at)}</td>
                  <td><Badge value={m.movement_type} /></td>
                  <td className={`right strong ${m.change > 0 ? "pos" : "neg"}`}>{m.change > 0 ? `+${m.change}` : m.change}</td>
                  <td className="right">{m.quantity_after}</td>
                  <td className="muted">{m.reference ?? m.note ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Modal>
  );
}
