"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { WorkspacePage } from "@/components/page-template";
import {
  ButtonLink,
  Card,
  EmptyState,
  ErrorState,
  Skeleton,
} from "@/components/ui";
import { CategoryName } from "@/components/category-name";
import { useCategories } from "@/lib/categories";
import { ApiClientError, getApi } from "@/lib/api-client";

type Offer = {
  item_id: string;
  price: number | null;
  original_price: number | null;
  currency_id: string | null;
  condition: string | null;
  free_shipping: boolean;
  captured_at_utc: string;
  raw_source_id: number;
};
type Detail = {
  product_id: string;
  name: string | null;
  brand: string | null;
  ranking_category_id: string | null;
  captured_at_utc: string;
  raw_source_id: number;
  offer_count: number;
  lowest_price: number | null;
  highest_price: number | null;
  visit_points: number;
  related_keyword_count: number;
  offers: Offer[];
  visits: {
    item_id: string;
    date_utc: string;
    visits: number;
    window_days: number | null;
  }[];
  keywords: {
    keyword: string;
    scope: string;
    category_id: string | null;
    relevance_position: number;
    raw_source_id: number;
  }[];
  categories: {
    offer_category_name: string | null;
    path: { name?: string }[];
    offer_count: number;
    raw_source_id: number;
  }[];
};
const money = (amount: number | null, currency = "CLP") =>
  amount === null
    ? "Sin precio observado"
    : new Intl.NumberFormat("es-CL", {
        style: "currency",
        currency,
        maximumFractionDigits: 0,
      }).format(amount);

export default function ProductDetailPage() {
  const categories = useCategories();
  const { productId } = useParams<{ productId: string }>();
  const product = useQuery({
    queryKey: ["product", productId],
    queryFn: () => getApi<Detail>(`/products/${encodeURIComponent(productId)}`),
  });
  if (product.isPending)
    return (
      <WorkspacePage
        eyebrow="Producto"
        title="Cargando producto"
        description="Consultando snapshots y evidencia."
      >
        <Skeleton className="h-72" />
      </WorkspacePage>
    );
  if (product.isError)
    return (
      <WorkspacePage
        eyebrow="Producto"
        title="Producto no disponible"
        description="El detalle depende de evidencia capturada."
      >
        <ErrorState
          message={
            product.error instanceof ApiClientError
              ? product.error.message
              : "No fue posible cargar el producto."
          }
        />
      </WorkspacePage>
    );
  const item = product.data;
  return (
    <WorkspacePage
      eyebrow="Producto"
      title={item.name || item.product_id}
      description="Producto, publicación/oferta e ítem se muestran por separado. Las visitas son tráfico observado, no ventas."
    >
      <ButtonLink variant="ghost" size="sm" href="/products">
        ← Volver a productos
      </ButtonLink>
      <div className="mt-4 grid gap-4 md:grid-cols-3">
        <Card>
          <p className="text-sm text-[var(--muted)]">
            Rango de precios observados
          </p>
          <p className="mt-2 font-semibold">
            {money(item.lowest_price)} — {money(item.highest_price)}
          </p>
          <p className="mt-2 text-xs text-[var(--muted)]">
            {item.offer_count} ofertas capturadas
          </p>
        </Card>
        <Card>
          <p className="text-sm text-[var(--muted)]">Visitas observadas</p>
          <p className="mt-2 text-2xl font-semibold">{item.visit_points}</p>
          <p className="mt-2 text-xs text-[var(--muted)]">
            Puntos de tráfico; no son ventas.
          </p>
        </Card>
        <Card>
          <p className="text-sm text-[var(--muted)]">Contexto</p>
          <p className="mt-2">{item.brand || "Marca no informada"}</p>
          <div className="mt-2 text-sm">
            Categoría del ranking:{" "}
            <CategoryName
              id={item.ranking_category_id}
              categories={categories.data?.items}
              empty="Categoría no informada"
            />
          </div>
        </Card>
      </div>
      <div className="mt-5 grid gap-5 xl:grid-cols-2">
        <Card>
          <h2 className="font-semibold">Ofertas observadas</h2>
          {item.offers.length ? (
            <div className="mt-3 overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="text-[var(--muted)]">
                    <th>Ítem</th>
                    <th>Precio</th>
                    <th>Condición</th>
                    <th>Evidencia</th>
                  </tr>
                </thead>
                <tbody>
                  {item.offers.map((offer) => (
                    <tr
                      className="border-t border-[var(--line)]"
                      key={`${offer.item_id}-${offer.raw_source_id}`}
                    >
                      <td className="py-2 pr-2">{offer.item_id}</td>
                      <td className="py-2 pr-2">
                        {money(offer.price, offer.currency_id || "CLP")}
                      </td>
                      <td className="py-2 pr-2">{offer.condition || "—"}</td>
                      <td className="py-2">
                        <ButtonLink
                          variant="ghost"
                          size="sm"
                          href={`/evidence/${offer.raw_source_id}`}
                        >
                          Evidencia original
                        </ButtonLink>
                        <span className="block text-xs text-[var(--muted)]">
                          RAW #{offer.raw_source_id}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState
              title="Sin ofertas capturadas"
              detail="Este snapshot de producto no contiene publicaciones observadas."
            />
          )}
        </Card>
        <Card>
          <h2 className="font-semibold">Términos relacionados</h2>
          {item.keywords.length ? (
            <ul className="mt-3 space-y-2 text-sm">
              {item.keywords.map((keyword) => (
                <li
                  className="border-t border-[var(--line)] pt-2"
                  key={`${keyword.keyword}-${keyword.raw_source_id}`}
                >
                  {keyword.keyword}{" "}
                  <span className="text-[var(--muted)]">
                    · posición de relevancia {keyword.relevance_position}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState
              title="Sin términos relacionados"
              detail="No se capturó un cruce término → producto para este producto."
            />
          )}
        </Card>
        <Card>
          <h2 className="font-semibold">Jerarquía de categoría</h2>
          {item.categories.length ? (
            item.categories.map((category) => (
              <div className="mt-3 text-sm" key={category.raw_source_id}>
                {category.path
                  .map((node) => node.name)
                  .filter(Boolean)
                  .join(" › ") ||
                  category.offer_category_name ||
                  "Sin jerarquía"}
              </div>
            ))
          ) : (
            <EmptyState
              title="Sin jerarquía disponible"
              detail="No se capturó una categoría de oferta para este producto."
            />
          )}
        </Card>
        <Card>
          <h2 className="font-semibold">Visitas por ítem</h2>
          {item.visits.length ? (
            <ul className="mt-3 space-y-2 text-sm">
              {item.visits.map((visit) => (
                <li
                  className="border-t border-[var(--line)] pt-2"
                  key={`${visit.item_id}-${visit.date_utc}`}
                >
                  {visit.item_id}: {visit.visits} visitas (
                  {visit.window_days || "—"} días)
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState
              title="Sin visitas capturadas"
              detail="La ausencia de visitas no permite inferir ventas ni demanda."
            />
          )}
        </Card>
      </div>
    </WorkspacePage>
  );
}
