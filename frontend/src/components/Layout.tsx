import { NavLink, Outlet } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  LayoutDashboard,
  Package,
  Truck,
  ShoppingCart,
  ClipboardList,
  BellRing,
  BarChart3,
  ArrowLeftRight,
  LogOut,
  Layers,
} from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import { api } from "../api/client";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/products", label: "Products", icon: Package },
  { to: "/stock", label: "Stock movements", icon: ArrowLeftRight },
  { to: "/orders", label: "Sales orders", icon: ShoppingCart },
  { to: "/purchase-orders", label: "Purchase orders", icon: ClipboardList },
  { to: "/suppliers", label: "Suppliers", icon: Truck },
  { to: "/alerts", label: "Low-stock alerts", icon: BellRing, badge: true },
  { to: "/reports", label: "Reports", icon: BarChart3 },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const { data: alertCount } = useQuery({
    queryKey: ["alerts", "count"],
    queryFn: () => api.get<{ open: number }>("/alerts/count"),
    refetchInterval: 30_000,
  });

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <Layers size={18} />
          </div>
          <span>StockPilot</span>
        </div>
        <nav>
          {NAV.map(({ to, label, icon: Icon, end, badge }) => (
            <NavLink key={to} to={to} end={end} className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
              <Icon size={18} />
              <span>{label}</span>
              {badge && !!alertCount?.open && <span className="nav-badge">{alertCount.open}</span>}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="avatar">{user?.full_name.split(" ").map((p) => p[0]).join("")}</div>
          <div className="user-meta">
            <strong>{user?.full_name}</strong>
            <span>{user?.role}</span>
          </div>
          <button className="icon-btn" onClick={logout} aria-label="Sign out" title="Sign out">
            <LogOut size={16} />
          </button>
        </div>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
