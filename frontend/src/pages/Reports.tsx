import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Download } from "lucide-react";
import { api } from "../api/client";
import type { InventoryReport, SalesReport } from "../api/types";
import { PageHeader, Spinner } from "../components/ui";
import { useToast } from "../components/Toast";
import { isoDay, money, moneyCompact, num, shortDate } from "../lib/format";

const PRESETS = [7, 30, 90];
const CATEGORY_COLORS = ["#4f46e5", "#0ea5e9", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#64748b"];

export default function Reports() {
  const toast = useToast();
  const today = new Date();
  const [range, setRange] = useState(() => ({
    start: isoDay(new Date(today.getTime() - 29 * 86400000)),
    end: isoDay(today),
  }));
  const params = { start_date: range.start, end_date: range.end };

  const sales = useQuery({
    queryKey: ["reports", "sales", range],
    queryFn: () => api.get<SalesReport>("/reports/sales", params),
  });
  const inventory = useQuery({
    queryKey: ["reports", "inventory"],
    queryFn: () => api.get<InventoryReport>("/reports/inventory"),
  });

  const preset = (days: number) =>
    setRange({ start: isoDay(new Date(Date.now() - (days - 1) * 86400000)), end: isoDay(new Date()) });

  const exportCsv = () =>
    api.download("/reports/sales.csv", params, `sales_${range.start}_${range.end}.csv`).catch((e) => toast(e.message, "error"));

  const s = sales.data?.summary;
  const margin = s && Number(s.revenue) ? (Number(s.gross_profit) / Number(s.revenue)) * 100 : 0;
  const daily = sales.data?.daily.map((d) => ({ ...d, revenue: Number(d.revenue), label: shortDate(d.date) })) ?? [];
  const catTotal = sales.data?.by_category.reduce((n, c) => n + Number(c.revenue), 0) ?? 0;

  return (
    <>
      <PageHeader title="Reports" subtitle="Sales performance and inventory valuation."
        actions={<button className="btn" onClick={exportCsv}><Download size={16} /> Export CSV</button>} />

      <div className="toolbar bare">
        <div className="segmented">
          {PRESETS.map((d) => (
            <button key={d} onClick={() => preset(d)}
              className={range.end === isoDay(new Date()) && range.start === isoDay(new Date(Date.now() - (d - 1) * 86400000)) ? "active" : ""}>
              Last {d} days
            </button>
          ))}
        </div>
        <div className="date-range">
          <input type="date" value={range.start} max={range.end} onChange={(e) => setRange({ ...range, start: e.target.value })} />
          <span className="muted">to</span>
          <input type="date" value={range.end} min={range.start} onChange={(e) => setRange({ ...range, end: e.target.value })} />
        </div>
      </div>

      {sales.isLoading || !s ? <Spinner /> : (
        <>
          <div className="stats-grid stats-4">
            <div className="card stat-simple"><span className="stat-label">Revenue</span><span className="stat-value">{money(s.revenue)}</span></div>
            <div className="card stat-simple"><span className="stat-label">Gross profit</span><span className="stat-value">{money(s.gross_profit)}</span><span className="stat-hint">{margin.toFixed(1)}% margin</span></div>
            <div className="card stat-simple"><span className="stat-label">Orders</span><span className="stat-value">{num(s.orders)}</span><span className="stat-hint">{num(s.units_sold)} units sold</span></div>
            <div className="card stat-simple"><span className="stat-label">Avg. order value</span><span className="stat-value">{money(s.average_order_value)}</span></div>
          </div>

          <section className="card">
            <div className="card-header"><h3>Daily revenue</h3></div>
            <div className="chart">
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={daily} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eef0f4" />
                  <XAxis dataKey="label" tickLine={false} axisLine={false} fontSize={12} minTickGap={16} />
                  <YAxis tickFormatter={(v) => moneyCompact(v)} tickLine={false} axisLine={false} fontSize={12} width={60} />
                  <Tooltip formatter={(v: number) => money(v)} cursor={{ fill: "#f1f5f9" }} />
                  <Bar dataKey="revenue" fill="#4f46e5" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </section>

          <div className="grid-2">
            <section className="card">
              <div className="card-header"><h3>Top products</h3></div>
              <table className="table compact">
                <thead><tr><th>#</th><th>Product</th><th className="right">Units</th><th className="right">Revenue</th></tr></thead>
                <tbody>
                  {sales.data!.top_products.map((p, i) => (
                    <tr key={p.product_id}>
                      <td className="muted">{i + 1}</td>
                      <td><div className="strong">{p.name}</div><div className="muted small mono">{p.sku}</div></td>
                      <td className="right">{num(p.units_sold)}</td>
                      <td className="right strong">{money(p.revenue)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
            <section className="card">
              <div className="card-header"><h3>Revenue by category</h3></div>
              <ul className="bar-list">
                {sales.data!.by_category.map((c, i) => {
                  const pct = catTotal ? (Number(c.revenue) / catTotal) * 100 : 0;
                  return (
                    <li key={c.category}>
                      <div className="bar-list-label"><span>{c.category}</span><span><strong>{money(c.revenue)}</strong> <span className="muted">· {pct.toFixed(0)}%</span></span></div>
                      <div className="meter"><div className="meter-fill" style={{ width: `${pct}%`, background: CATEGORY_COLORS[i % CATEGORY_COLORS.length] }} /></div>
                    </li>
                  );
                })}
              </ul>
            </section>
          </div>
        </>
      )}

      {inventory.data && (
        <section className="card">
          <div className="card-header">
            <h3>Inventory valuation</h3>
            <span className="muted">{num(inventory.data.total_units)} units across {inventory.data.total_products} products</span>
          </div>
          <table className="table">
            <thead><tr><th>Category</th><th className="right">Products</th><th className="right">Units</th><th className="right">Cost value</th><th className="right">Retail value</th><th className="right">Potential profit</th></tr></thead>
            <tbody>
              {inventory.data.by_category.map((r) => (
                <tr key={r.category}>
                  <td className="strong">{r.category}</td>
                  <td className="right">{r.products}</td>
                  <td className="right">{num(r.units)}</td>
                  <td className="right">{money(r.cost_value)}</td>
                  <td className="right">{money(r.retail_value)}</td>
                  <td className="right pos">{money(Number(r.retail_value) - Number(r.cost_value))}</td>
                </tr>
              ))}
              <tr className="total-row">
                <td>Total</td><td className="right">{inventory.data.total_products}</td><td className="right">{num(inventory.data.total_units)}</td>
                <td className="right">{money(inventory.data.cost_value)}</td><td className="right">{money(inventory.data.retail_value)}</td>
                <td className="right pos">{money(Number(inventory.data.retail_value) - Number(inventory.data.cost_value))}</td>
              </tr>
            </tbody>
          </table>
        </section>
      )}
    </>
  );
}
