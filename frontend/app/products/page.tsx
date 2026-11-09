"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { CategoryName } from "@/components/category-name";
import { WorkspacePage } from "@/components/page-template";
import {
  Button,
  ButtonLink,
  Card,
  EmptyState,
  ErrorState,
  Skeleton,
} from "@/components/ui";
import { getApi } from "@/lib/api-client";
import { useCategories } from "@/lib/categories";

type Product = {
  product_id: string;
  name: string | null;
  brand: string | null;
  domain_id: string | null;
  ranking_category_id: string | null;
  highlight_position: number | null;
  captured_at_utc: string;
  raw_source_id: number;
};
type Result = { items: Product[]; page: { next_cursor: number | null } };

export default function ProductsPage() {
  const [query, setQuery] = useState("");
  const [cursor, setCursor] = useState(0);
  const categories = useCategories();
  const products = useQuery({
    queryKey: ["products", query, cursor],
    queryFn: ({ signal }) =>
      getApi<Result>(
        `/products?limit=50&cursor=${cursor}${query ? `&query=${encodeURIComponent(query)}` : ""}`,
        { signal },
      ),
  });
  return (
    <WorkspacePage
      eyebrow="Explorador"
      title="Productos"
      description="Observaciones de productos destacados. Producto, oferta e ítem son entidades distintas; las visitas no se interpretan como ventas."
    >
      <Card>
        <label className="text-sm font-medium">
          Buscar producto, ID, marca o dominio
          <input
            className="mt-2 block w-full rounded-lg border border-[var(--line)] bg-[var(--background)] px-3 py-2"
            placeholder="Ej.: Armaf"
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setCursor(0);
            }}
          />
        </label>
      </Card>
      {categories.isError ? (
        <p className="mt-3 text-sm text-[var(--muted)]">
          No se pudieron cargar los nombres de categorías; se muestran sus
          códigos.
        </p>
      ) : null}
      <div className="mt-5">
        {products.isPending ? (
          <Skeleton className="h-64" />
        ) : products.isError ? (
          <ErrorState message="No fue posible cargar productos. Vuelve a intentarlo más tarde." />
        ) : products.data.items.length === 0 ? (
          <EmptyState
            title="Sin productos para este filtro"
            detail="Prueba nombre, ID, marca o dominio diferente."
          />
        ) : (
          <>
            <div
              className="table-scroll"
              role="region"
              aria-label="Tabla de productos, desplazamiento horizontal"
              tabIndex={0}
            >
              <table className="data-table">
                <caption className="sr-only">Productos capturados</caption>
                <thead>
                  <tr>
                    <th scope="col">Producto</th>
                    <th scope="col">Marca</th>
                    <th scope="col">Categoría y fecha</th>
                    <th scope="col">Evidencia</th>
                  </tr>
                </thead>
                <tbody>
                  {products.data.items.map((product) => (
                    <tr key={`${product.product_id}-${product.raw_source_id}`}>
                      <td>
                        <ButtonLink
                          className="justify-start text-left"
                          variant="ghost"
                          size="sm"
                          href={`/products/${encodeURIComponent(product.product_id)}`}
                        >
                          {product.name || product.product_id}
                        </ButtonLink>
                        <p className="text-xs text-[var(--muted)]">
                          {product.product_id}
                        </p>
                      </td>
                      <td>
                        {product.brand || "Marca no informada"}
                        {product.domain_id ? (
                          <details className="mt-2 text-xs text-[var(--muted)]">
                            <summary className="min-h-11 cursor-pointer py-3">
                              Ver dominio técnico
                            </summary>
                            <p className="break-all">{product.domain_id}</p>
                          </details>
                        ) : null}
                      </td>
                      <td>
                        <CategoryName
                          id={product.ranking_category_id}
                          categories={categories.data?.items}
                          empty="Categoría no informada"
                        />
                        <p className="mt-2 text-xs text-[var(--muted)]">
                          <time dateTime={product.captured_at_utc}>
                            {new Date(
                              product.captured_at_utc,
                            ).toLocaleDateString("es-CL")}
                          </time>
                        </p>
                      </td>
                      <td>
                        <ButtonLink
                          variant="ghost"
                          size="sm"
                          href={`/evidence/${product.raw_source_id}`}
                        >
                          Evidencia original
                        </ButtonLink>
                        <span className="block text-xs text-[var(--muted)]">
                          RAW #{product.raw_source_id}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="mt-4 flex flex-wrap justify-end gap-3">
              <Button
                disabled={cursor === 0}
                aria-describedby={
                  cursor === 0 ? "products-first-page" : undefined
                }
                onClick={() => setCursor(0)}
              >
                Primera página
              </Button>
              <Button
                disabled={products.data.page.next_cursor === null}
                aria-describedby={
                  products.data.page.next_cursor === null
                    ? "products-last-page"
                    : undefined
                }
                onClick={() =>
                  setCursor(products.data.page.next_cursor ?? cursor)
                }
              >
                Siguiente página
              </Button>
            </div>
            <p className="mt-2 text-right text-xs text-[var(--muted)]">
              {cursor === 0 ? (
                <span id="products-first-page">
                  Estás en la primera página.{" "}
                </span>
              ) : null}
              {products.data.page.next_cursor === null ? (
                <span id="products-last-page">No hay más resultados.</span>
              ) : null}
            </p>
          </>
        )}
      </div>
    </WorkspacePage>
  );
}
