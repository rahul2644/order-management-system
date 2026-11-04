import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import type { Category, Product, Page, Supplier } from "../api/types";

export function useDebounced<T>(value: T, delay = 300): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return v;
}

export const useCategories = () =>
  useQuery({ queryKey: ["categories"], queryFn: () => api.get<Category[]>("/categories") });

export const useSuppliers = () =>
  useQuery({ queryKey: ["suppliers"], queryFn: () => api.get<Supplier[]>("/suppliers") });

/** All active products, for pickers in order forms. */
export const useAllProducts = () =>
  useQuery({
    queryKey: ["products", "all"],
    queryFn: () => api.get<Page<Product>>("/products", { size: 200 }).then((p) => p.items),
  });
