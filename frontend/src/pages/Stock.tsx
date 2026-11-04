import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import type { MovementType, StockMovement } from "../api/types";
import { Badge, Empty, PageHeader, Spinner } from "../components/ui";
import { dateTime } from "../lib/format";

const TYPES: (MovementType | "")[] = ["", "sale", "purchase", "adjustment", "return"];

export default function Stock() {
  const [type, setType] = useState<MovementType | "">("");
  const { data, isLoading } = useQuery({
    queryKey: ["movements", "all", type],
    queryFn: () => api.get<StockMovement[]>("/stock/movements", { movement_type: type, limit: 200 }),
  });

  return (
    <>
      <PageHeader title="Stock movements" subtitle="An audit trail of every change to on-hand quantity." />
      <div className="card">
        <div className="toolbar">
          <div className="segmented">
            {TYPES.map((t) => (
              <button key={t || "all"} className={type === t ? "active" : ""} onClick={() => setType(t)}>
                {t ? t[0].toUpperCase() + t.slice(1) : "All"}
              </button>
            ))}
          </div>
        </div>
        {isLoading ? <Spinner /> : !data?.length ? <Empty message="No stock movements yet." /> : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr><th>When</th><th>Product</th><th>Type</th><th className="right">Change</th><th className="right">Balance</th><th>Reference / note</th></tr>
              </thead>
              <tbody>
                {data.map((m) => (
                  <tr key={m.id}>
                    <td className="nowrap">{dateTime(m.created_at)}</td>
                    <td>
                      <div className="strong">{m.product_name}</div>
                      <div className="muted small mono">{m.product_sku}</div>
                    </td>
                    <td><Badge value={m.movement_type} /></td>
                    <td className={`right strong ${m.change > 0 ? "pos" : "neg"}`}>{m.change > 0 ? `+${m.change}` : m.change}</td>
                    <td className="right">{m.quantity_after}</td>
                    <td className="muted">{[m.reference, m.note].filter(Boolean).join(" · ") || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
