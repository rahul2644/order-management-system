import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { BellRing, CheckCircle2, Wand2 } from "lucide-react";
import { api } from "../api/client";
import type { Alert } from "../api/types";
import { Badge, Empty, PageHeader, Spinner } from "../components/ui";
import { dateTime, timeAgo } from "../lib/format";
import { useGenerateFromAlerts } from "./PurchaseOrders";

export default function Alerts() {
  const [status, setStatus] = useState<"open" | "resolved">("open");
  const generate = useGenerateFromAlerts();
  const { data, isLoading } = useQuery({
    queryKey: ["alerts", status],
    queryFn: () => api.get<Alert[]>("/alerts", { status }),
  });

  return (
    <>
      <PageHeader title="Low-stock alerts"
        subtitle="Raised automatically when a product falls to its reorder level and resolved when it's restocked."
        actions={status === "open" && !!data?.length && (
          <button className="btn btn-primary" onClick={() => generate.mutate()} disabled={generate.isPending}>
            <Wand2 size={16} /> Draft purchase orders
          </button>
        )} />
      {generate.isSuccess && generate.data.length > 0 && (
        <div className="banner">
          Drafted {generate.data.map((p) => p.po_number).join(", ")}. <Link to="/purchase-orders" className="link">Review purchase orders →</Link>
        </div>
      )}
      <div className="card">
        <div className="toolbar">
          <div className="segmented">
            <button className={status === "open" ? "active" : ""} onClick={() => setStatus("open")}>Open</button>
            <button className={status === "resolved" ? "active" : ""} onClick={() => setStatus("resolved")}>Resolved</button>
          </div>
        </div>
        {isLoading ? <Spinner /> : !data?.length ? (
          <Empty message={status === "open" ? "No open alerts. Everything is above its reorder level." : "No resolved alerts yet."} />
        ) : (
          <ul className="alert-list">
            {data.map((a) => {
              const pct = Math.min(100, (a.current_quantity / Math.max(1, a.reorder_level)) * 100);
              return (
                <li key={a.id} className="alert-item">
                  <div className={`alert-icon ${a.status}`}>{a.status === "open" ? <BellRing size={18} /> : <CheckCircle2 size={18} />}</div>
                  <div className="alert-body">
                    <div className="strong">{a.product_name} <span className="muted mono small">{a.product_sku}</span></div>
                    <div className="muted small">
                      Dropped to {a.quantity_at_trigger} units (reorder level {a.reorder_level}) · {timeAgo(a.created_at)}
                      {a.resolved_at && ` · resolved ${dateTime(a.resolved_at)}`}
                    </div>
                    {a.status === "open" && (
                      <div className="meter"><div className={`meter-fill ${a.current_quantity === 0 ? "red" : "amber"}`} style={{ width: `${pct}%` }} /></div>
                    )}
                  </div>
                  <div className="alert-qty">
                    <div className="stat-value small-value">{a.current_quantity}</div>
                    <div className="muted small">on hand</div>
                  </div>
                  <Badge value={a.status} />
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </>
  );
}
