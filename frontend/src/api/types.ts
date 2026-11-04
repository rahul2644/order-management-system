export type Role = "admin" | "staff";
export type OrderStatus = "pending" | "confirmed" | "shipped" | "delivered" | "cancelled";
export type POStatus = "draft" | "ordered" | "received" | "cancelled";
export type MovementType = "purchase" | "sale" | "adjustment" | "return";

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
}

export interface Category {
  id: number;
  name: string;
}

export interface Supplier {
  id: number;
  name: string;
  contact_name: string | null;
  email: string | null;
  phone: string | null;
  address: string | null;
  lead_time_days: number;
  product_count: number;
  created_at: string;
}

export interface Product {
  id: number;
  sku: string;
  name: string;
  description: string | null;
  category_id: number | null;
  supplier_id: number | null;
  category: Category | null;
  supplier_name: string | null;
  unit_price: string;
  cost_price: string;
  quantity: number;
  reorder_level: number;
  reorder_quantity: number;
  is_active: boolean;
  is_low_stock: boolean;
  updated_at: string;
}

export interface StockMovement {
  id: number;
  product_id: number;
  product_name: string | null;
  product_sku: string | null;
  change: number;
  quantity_after: number;
  movement_type: MovementType;
  reference: string | null;
  note: string | null;
  created_at: string;
}

export interface OrderItem {
  id: number;
  product_id: number;
  product_name: string;
  product_sku: string;
  quantity: number;
  unit_price: string;
}

export interface Order {
  id: number;
  order_number: string;
  customer_name: string;
  customer_email: string | null;
  status: OrderStatus;
  notes: string | null;
  total: string;
  created_at: string;
  confirmed_at: string | null;
  items: OrderItem[];
}

export interface PurchaseOrderItem {
  id: number;
  product_id: number;
  product_name: string;
  product_sku: string;
  quantity: number;
  unit_cost: string;
}

export interface PurchaseOrder {
  id: number;
  po_number: string;
  supplier_id: number;
  supplier_name: string;
  status: POStatus;
  expected_date: string | null;
  received_at: string | null;
  notes: string | null;
  total: string;
  created_at: string;
  items: PurchaseOrderItem[];
}

export interface Alert {
  id: number;
  product_id: number;
  product_name: string;
  product_sku: string;
  current_quantity: number;
  quantity_at_trigger: number;
  reorder_level: number;
  status: "open" | "resolved";
  created_at: string;
  resolved_at: string | null;
}

export interface DailySales {
  date: string;
  revenue: string;
  orders: number;
}

export interface SalesReport {
  start_date: string;
  end_date: string;
  summary: {
    revenue: string;
    cost: string;
    gross_profit: string;
    orders: number;
    units_sold: number;
    average_order_value: string;
  };
  daily: DailySales[];
  top_products: { product_id: number; sku: string; name: string; units_sold: number; revenue: string }[];
  by_category: { category: string; revenue: string; units_sold: number }[];
}

export interface InventoryReport {
  total_products: number;
  total_units: number;
  cost_value: string;
  retail_value: string;
  by_category: { category: string; products: number; units: number; cost_value: string; retail_value: string }[];
}

export interface Dashboard {
  total_products: number;
  total_suppliers: number;
  inventory_value: string;
  low_stock_count: number;
  open_alerts: number;
  pending_orders: number;
  revenue_30d: string;
  orders_30d: number;
  revenue_trend: DailySales[];
  order_status_breakdown: Record<string, number>;
  recent_orders: Order[];
  low_stock_products: Product[];
}
