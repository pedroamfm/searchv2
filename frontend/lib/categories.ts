"use client";

import { useQuery } from "@tanstack/react-query";
import { getApi } from "@/lib/api-client";

export type Category = { category_id: string; name: string | null };
export function useCategories() {
  return useQuery({
    queryKey: ["categories"],
    queryFn: ({ signal }) =>
      getApi<{ items: Category[] }>("/categories", { signal }),
  });
}
export function categoryLabel(
  id: string | null,
  categories?: Category[],
  empty = "General",
) {
  if (!id) return empty;
  return (
    categories?.find((category) => category.category_id === id && category.name)
      ?.name || `Código ${id} · nombre no disponible`
  );
}
