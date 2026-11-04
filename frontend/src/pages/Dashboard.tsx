import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis, PieChart, Pie, Cell } from "recharts";
import { DollarSign, Package, AlertTriangle, ShoppingCart, Warehouse, Truck } from "lucide-react";
import { api } from "../api/client";
import type { Dashboard as DashboardData } from "../api/types";
import { Badge, PageHeader, Spinner, StockPill } from "../components/ui";
import { money, moneyCompact, num, shortDate, timeAgo } from "../lib/format";

const STATUS_COLORS: Record<string, string> = {
  pending: "#f59e0b",
  confirmed: "#3b82f6",
  shipped: "#8b5cf6",
  delivered: "#10b981",
  cancelled: "#ef4444",
};

function Stat({ icon: Icon, label, value, hint, tone = "indigo", to }: {
  icon: typeof Package; label: string; value: string; hint?: string; tone?: string; to?: string;
}) {
  const body = (
    <div className="stat card">
      <div className={`stat-icon tone-${tone}`}><Icon size={20} /></div>
      <div>
        <div className="stat-label">{label}</div>
        <div className="stat-value">{value}</div>
        {hint && <div className="stat-hint">{hint}</div>}
      </div>
    </div>
  );
  return to ? <Link to={to} className="stat-link">{body}</Link> : body;
}

export default function Dashboard() {
  const { data, isLoading } = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => api.get<DashboardData>("/dashboard"),
  });

  if (isLoading || !data) return <Spinner />;

  const trend = data.revenue_trend.map((d) => ({ ...d, revenue: Number(d.revenue), label: shortDate(d.date) }));
  const statusData = Object.entries(data.order_status_breakdown).map(([name, value]) => ({ name, value }));

  return (
    <>
      <PageHeader title="Dashboard" subtitle="A snapshot of your inventory and sales over the last 30 days." />

      <div className="stats-grid stats-3">
        <Stat icon={DollarSign} label="Revenue (30d)" value={money(data.revenue_30d)} hint={`${num(data.orders_30d)} orders`} tone="green" to="/reports" />
        <Stat icon={Warehouse} label="Inventory value" value={money(data.inventory_value)} hint="at cost" tone="indigo" to="/reports" />
        <Stat icon={ShoppingCart} label="Pending orders" value={num(data.pending_orders)} hint="awaiting confirmation" tone="amber" to="/orders" />
        <Stat icon={AlertTriangle} label="Low-stock alerts" value={num(data.open_alerts)} hint={`${data.low_stock_count} products at or below reorder level`} tone="red" to="/alerts" />
        <Stat icon={Package} label="Active products" value={num(data.total_products)} tone="blue" to="/products" />
        <Stat icon={Truck} label="Suppliers" value={num(data.total_suppliers)} tone="violet" to="/suppliers" />
      </div>

      <div className="grid-2-1">
        <section className="card">
          <div className="card-header">
            <h3>Revenue trend</h3>
            <span className="muted">Last 30 days</span>
          </div>
          <div className="chart">
            <ResponsiveContainer width="100%" height={260}>
              <AreaChart data={trend} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="rev" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#4f46e5" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="#4f46e5" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eef0f4" />
                <XAxis dataKey="label" tickLine={false} axisLine={false} fontSize={12} interval={4} />
                <YAxis tickFormatter={(v) => moneyCompact(v)} tickLine={false} axisLine={false} fontSize={12} width={60} />
                <Tooltip formatter={(v: number) => money(v)} labelFormatter={(l) => l} />
                <Area type="monotone" dataKey="revenue" stroke="#4f46e5" strokeWidth={2} fill="url(#rev)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </section>

        <section className="card">
          <div className="card-header">
            <h3>Orders by status</h3>
          </div>
          <div className="chart">
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={statusData} dataKey="value" nameKey="name" innerRadius={55} outerRadius={85} paddingAngle={2}>
                  {statusData.map((s) => <Cell key={s.name} fill={STATUS_COLORS[s.name] ?? "#94a3b8"} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <ul className="legend">
            {statusData.map((s) => (
              <li key={s.name}>
                <span className="legend-dot" style={{ background: STATUS_COLORS[s.name] }} />
                <span className="cap">{s.name}</span>
                <strong>{num(s.value)}</strong>
              </li>
            ))}
          </ul>
        </section>
      </div>

      <div className="grid-2">
        <section className="card">
          <div className="card-header">
            <h3>Recent orders</h3>
            <Link to="/orders" className="link">View all</Link>
          </div>
          <table className="table">
            <tbody>
              {data.recent_orders.map((o) => (
                <tr key={o.id}>
                  <td>
                    <div className="strong">{o.order_number}</div>
                    <div className="muted small">{o.customer_name}</div>
                  </td>
                  <td><Badge value={o.status} /></td>
                  <td className="right">
                    <div className="strong">{money(o.total)}</div>
                    <div className="muted small">{timeAgo(o.created_at)}</div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section className="card">
          <div className="card-header">
            <h3>Needs restocking</h3>
            <Link to="/alerts" className="link">Manage alerts</Link>
          </div>
          <table className="table">
            <tbody>
              {data.low_stock_products.map((p) => (
                <tr key={p.id}>
                  <td>
                    <div className="strong">{p.name}</div>
                    <div className="muted small">{p.sku} · {p.supplier_name}</div>
                  </td>
                  <td className="right"><StockPill quantity={p.quantity} reorderLevel={p.reorder_level} /></td>
                </tr>
              ))}
              {data.low_stock_products.length === 0 && (
                <tr><td className="muted">Everything is well stocked.</td></tr>
              )}
            </tbody>
          </table>
        </section>
      </div>
    </>
  );
}
