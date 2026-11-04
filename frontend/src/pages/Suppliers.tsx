import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Search, Mail, Phone, Pencil, Trash2, Clock } from "lucide-react";
import { api } from "../api/client";
import type { Supplier } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { Empty, ErrorText, Field, Modal, PageHeader, Spinner } from "../components/ui";
import { useToast } from "../components/Toast";
import { useDebounced } from "../lib/hooks";

export default function Suppliers() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const toast = useToast();
  const [q, setQ] = useState("");
  const [editing, setEditing] = useState<Supplier | "new" | null>(null);
  const search = useDebounced(q);
  const { data, isLoading } = useQuery({
    queryKey: ["suppliers", search],
    queryFn: () => api.get<Supplier[]>("/suppliers", { q: search }),
  });
  const remove = useMutation({
    mutationFn: (id: number) => api.delete(`/suppliers/${id}`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["suppliers"] }); toast("Supplier deleted"); },
    onError: (e: Error) => toast(e.message, "error"),
  });

  return (
    <>
      <PageHeader title="Suppliers" subtitle="Vendors you buy stock from."
        actions={<button className="btn btn-primary" onClick={() => setEditing("new")}><Plus size={16} /> Add supplier</button>} />
      <div className="toolbar bare">
        <div className="search">
          <Search size={16} />
          <input placeholder="Search suppliers…" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
      </div>
      {isLoading ? <Spinner /> : !data?.length ? <Empty message="No suppliers yet." /> : (
        <div className="card-grid">
          {data.map((s) => (
            <article key={s.id} className="card supplier-card">
              <header>
                <div className="avatar avatar-lg">{s.name.split(" ").slice(0, 2).map((w) => w[0]).join("")}</div>
                <div>
                  <h3>{s.name}</h3>
                  <div className="muted small">{s.contact_name ?? "No contact"}</div>
                </div>
                <div className="row-actions">
                  <button className="icon-btn" onClick={() => setEditing(s)} title="Edit"><Pencil size={15} /></button>
                  {user?.role === "admin" && (
                    <button className="icon-btn danger" title="Delete"
                      onClick={() => window.confirm(`Delete ${s.name}?`) && remove.mutate(s.id)}><Trash2 size={15} /></button>
                  )}
                </div>
              </header>
              <ul className="supplier-meta">
                {s.email && <li><Mail size={14} /> <a href={`mailto:${s.email}`}>{s.email}</a></li>}
                {s.phone && <li><Phone size={14} /> {s.phone}</li>}
                <li><Clock size={14} /> {s.lead_time_days}-day lead time</li>
              </ul>
              <footer><strong>{s.product_count}</strong> <span className="muted">products supplied</span></footer>
            </article>
          ))}
        </div>
      )}
      {editing && <SupplierForm supplier={editing === "new" ? null : editing} onClose={() => setEditing(null)} />}
    </>
  );
}

function SupplierForm({ supplier, onClose }: { supplier: Supplier | null; onClose: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [form, setForm] = useState({
    name: supplier?.name ?? "",
    contact_name: supplier?.contact_name ?? "",
    email: supplier?.email ?? "",
    phone: supplier?.phone ?? "",
    address: supplier?.address ?? "",
    lead_time_days: String(supplier?.lead_time_days ?? 7),
  });
  const set = (k: keyof typeof form) => (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value });
  const save = useMutation({
    mutationFn: () => {
      const body = {
        ...form,
        contact_name: form.contact_name || null,
        email: form.email || null,
        phone: form.phone || null,
        address: form.address || null,
        lead_time_days: Number(form.lead_time_days),
      };
      return supplier ? api.patch(`/suppliers/${supplier.id}`, body) : api.post("/suppliers", body);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["suppliers"] });
      toast(supplier ? "Supplier updated" : "Supplier added");
      onClose();
    },
  });
  return (
    <Modal title={supplier ? `Edit ${supplier.name}` : "New supplier"} onClose={onClose}
      footer={<>
        <button className="btn" onClick={onClose}>Cancel</button>
        <button className="btn btn-primary" form="supplier-form" disabled={save.isPending}>Save</button>
      </>}>
      <form id="supplier-form" className="form-grid" onSubmit={(e: FormEvent) => { e.preventDefault(); save.mutate(); }}>
        <div className="span-2"><Field label="Company name"><input value={form.name} onChange={set("name")} required /></Field></div>
        <Field label="Contact name"><input value={form.contact_name} onChange={set("contact_name")} /></Field>
        <Field label="Lead time (days)"><input type="number" min="0" value={form.lead_time_days} onChange={set("lead_time_days")} /></Field>
        <Field label="Email"><input type="email" value={form.email} onChange={set("email")} /></Field>
        <Field label="Phone"><input value={form.phone} onChange={set("phone")} /></Field>
        <div className="span-2"><Field label="Address"><textarea rows={2} value={form.address} onChange={set("address")} /></Field></div>
        <div className="span-2"><ErrorText error={save.error} /></div>
      </form>
    </Modal>
  );
}
