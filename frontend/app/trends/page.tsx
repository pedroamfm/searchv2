"use client";

import { useQuery } from "@tanstack/react-query";
import { useCallback, useState } from "react";
import { CategoryName } from "@/components/category-name";
import { HistoryPanel } from "@/components/history-panel";
import { WorkspacePage } from "@/components/page-template";
import {
  Badge,
  Button,
  ButtonLink,
  Card,
  EmptyState,
  ErrorState,
  Skeleton,
} from "@/components/ui";
import { getApi } from "@/lib/api-client";
import { categoryLabel, useCategories } from "@/lib/categories";

type Trend = {
  source_code: string;
  site_id: string;
  keyword: string;
  position: number;
  previous_position: number | null;
  change: "new" | "up" | "down" | "unchanged";
  scope: "general" | "category";
  category_id: string | null;
  captured_at_utc: string;
  raw_source_id: number;
};
type TrendResult = { items: Trend[]; page: { next_cursor: number | null } };
const changeLabel = {
  new: "Nueva",
  up: "Sube",
  down: "Baja",
  unchanged: "Sin cambio",
};
function tone(change: Trend["change"]): "neutral" | "success" | "warning" {
  return change === "up"
    ? "success"
    : change === "down"
      ? "warning"
      : "neutral";
}

export default function TrendsPage() {
  const [keyword, setKeyword] = useState("");
  const [scope, setScope] = useState("");
  const [category, setCategory] = useState("");
  const [cursor, setCursor] = useState(0);
  const [selected, setSelected] = useState<Trend | null>(null);
  const [opener, setOpener] = useState<HTMLElement | null>(null);
  const closeHistory = useCallback(() => setSelected(null), []);
  const categories = useCategories();
  const filters = new URLSearchParams({ limit: "50", cursor: String(cursor) });
  if (keyword) filters.set("keyword", keyword);
  if (scope) filters.set("scope", scope);
  if (category) filters.set("category_id", category);
  const trends = useQuery({
    queryKey: ["trends", keyword, scope, category, cursor],
    queryFn: ({ signal }) =>
      getApi<TrendResult>(`/trends?${filters}`, { signal }),
  });
  const history = useQuery({
    queryKey: [
      "trend-history",
      selected?.source_code,
      selected?.site_id,
      selected?.scope,
      selected?.category_id,
      selected?.keyword,
    ],
    enabled: selected !== null,
    queryFn: ({ signal }) =>
      getApi<{ items: Trend[] }>(
        `/trends/history?${new URLSearchParams({ source_code: selected!.source_code, site_id: selected!.site_id, scope: selected!.scope, keyword: selected!.keyword, ...(selected!.category_id ? { category_id: selected!.category_id } : {}) })}`,
        { signal },
      ),
  });
  const reset = () => setCursor(0);
  return (
    <WorkspacePage
      eyebrow="Explorador"
      title="Tendencias"
      description="La posición expresa interés relativo dentro de su ranking; no representa volumen absoluto ni permite comparar categorías entre sí."
    >
      <Card>
        <div className="grid gap-4 md:grid-cols-3">
          <label className="text-sm font-medium">
            Buscar término
            <input
              className="mt-2 block w-full rounded-lg border border-[var(--line)] bg-[var(--background)] px-3 py-2"
              placeholder="Ej.: alarma"
              value={keyword}
              onChange={(event) => {
                setKeyword(event.target.value);
                reset();
              }}
            />
          </label>
          <label className="text-sm font-medium">
            Alcance
            <select
              className="mt-2 block w-full rounded-lg border border-[var(--line)] bg-[var(--background)] px-3 py-2"
              value={scope}
              onChange={(event) => {
                setScope(event.target.value);
                reset();
              }}
            >
              <option value="">Todos</option>
              <option value="general">General</option>
              <option value="category">Categoría</option>
            </select>
          </label>
          <label className="text-sm font-medium">
            Categoría
            <select
              className="mt-2 block w-full rounded-lg border border-[var(--line)] bg-[var(--background)] px-3 py-2"
              value={category}
              onChange={(event) => {
                setCategory(event.target.value);
                reset();
              }}
            >
              <option value="">Todas</option>
              {categories.data?.items.map((item) => (
                <option
                  key={`${item.category_id}-${item.name}`}
                  value={item.category_id}
                >
                  {categoryLabel(item.category_id, categories.data.items)}
                </option>
              ))}
            </select>
          </label>
        </div>
      </Card>
      {categories.isError ? (
        <p className="mt-3 text-sm text-[var(--muted)]">
          No se pudieron cargar los nombres de categorías; se muestran sus
          códigos.
        </p>
      ) : null}
      <div className="mt-5">
        {trends.isPending ? (
          <Skeleton className="h-64" />
        ) : trends.isError ? (
          <ErrorState message="No fue posible cargar tendencias. Vuelve a intentarlo más tarde." />
        ) : trends.data.items.length === 0 ? (
          <EmptyState
            title="Sin tendencias para este filtro"
            detail="Prueba otro criterio o espera una nueva captura."
          />
        ) : (
          <>
            <div
              className="table-scroll"
              role="region"
              aria-label="Tabla de tendencias, desplazamiento horizontal"
              tabIndex={0}
            >
              <table className="data-table">
                <caption className="sr-only">Tendencias capturadas</caption>
                <thead>
                  <tr>
                    <th scope="col">Posición</th>
                    <th scope="col">Término</th>
                    <th scope="col">Cambio</th>
                    <th scope="col">Categoría</th>
                    <th scope="col">Fecha</th>
                    <th scope="col">Evidencia</th>
                  </tr>
                </thead>
                <tbody>
                  {trends.data.items.map((trend) => (
                    <tr key={`${trend.raw_source_id}-${trend.position}`}>
                      <td>{trend.position}</td>
                      <td>
                        <Button
                          variant="ghost"
                          size="sm"
                          aria-label={`Ver historial de ${trend.keyword}`}
                          aria-haspopup="dialog"
                          onClick={(event) => {
                            setOpener(event.currentTarget);
                            setSelected(trend);
                          }}
                        >
                          {trend.keyword}
                        </Button>
                      </td>
                      <td>
                        <Badge tone={tone(trend.change)}>
                          {changeLabel[trend.change]}
                          {trend.previous_position !== null
                            ? ` · antes ${trend.previous_position}`
                            : ""}
                        </Badge>
                      </td>
                      <td>
                        <CategoryName
                          id={trend.category_id}
                          categories={categories.data?.items}
                        />
                      </td>
                      <td className="text-[var(--muted)]">
                        <time dateTime={trend.captured_at_utc}>
                          {new Date(trend.captured_at_utc).toLocaleDateString(
                            "es-CL",
                          )}
                        </time>
                      </td>
                      <td>
                        <ButtonLink
                          variant="ghost"
                          size="sm"
                          href={`/evidence/${trend.raw_source_id}`}
                        >
                          Evidencia original
                        </ButtonLink>
                        <span className="block text-xs text-[var(--muted)]">
                          RAW #{trend.raw_source_id}
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
                  cursor === 0 ? "trends-first-page" : undefined
                }
                onClick={() => setCursor(0)}
              >
                Primera página
              </Button>
              <Button
                disabled={trends.data.page.next_cursor === null}
                aria-describedby={
                  trends.data.page.next_cursor === null
                    ? "trends-last-page"
                    : undefined
                }
                onClick={() =>
                  setCursor(trends.data.page.next_cursor ?? cursor)
                }
              >
                Siguiente página
              </Button>
            </div>
            <p className="mt-2 text-right text-xs text-[var(--muted)]">
              {cursor === 0 ? (
                <span id="trends-first-page">Estás en la primera página. </span>
              ) : null}
              {trends.data.page.next_cursor === null ? (
                <span id="trends-last-page">No hay más resultados.</span>
              ) : null}
            </p>
          </>
        )}
      </div>
      {selected ? (
        <HistoryPanel
          title={`Historial: ${selected.keyword}`}
          description={`${categoryLabel(selected.category_id, categories.data?.items, "Ranking general")}${selected.category_id ? ` (${selected.category_id})` : ""}. Sólo se muestran observaciones capturadas. La posición no equivale a volumen.`}
          opener={opener}
          onClose={closeHistory}
        >
          {history.isPending ? (
            <div role="status">
              <p className="mb-3 text-sm text-[var(--muted)]">
                Cargando historial…
              </p>
              <Skeleton className="h-24" />
            </div>
          ) : history.isError ? (
            <>
              <ErrorState message="No fue posible cargar el historial. No se pueden confirmar las observaciones." />
              <Button className="mt-3" onClick={() => history.refetch()}>
                Reintentar consulta
              </Button>
            </>
          ) : history.data.items.length ? (
            <>
              <p className="mb-4 text-sm text-[var(--muted)]" role="status">
                {history.data.items.length}{" "}
                {history.data.items.length === 1
                  ? "observación disponible"
                  : "observaciones disponibles"}
              </p>
              <ol className="space-y-3 text-sm">
                {history.data.items.map((item) => (
                  <li
                    key={`${item.captured_at_utc}-${item.raw_source_id}`}
                    className="flex flex-wrap justify-between gap-3 border-t border-[var(--line)] pt-3"
                  >
                    <time dateTime={item.captured_at_utc}>
                      {new Date(item.captured_at_utc).toLocaleString("es-CL")}
                    </time>
                    <span className="font-medium">
                      Posición {item.position}
                    </span>
                  </li>
                ))}
              </ol>
            </>
          ) : (
            <EmptyState
              title="Sin observaciones disponibles"
              detail="La ausencia de observaciones no es un valor cero ni permite inferir una evolución."
            />
          )}
        </HistoryPanel>
      ) : null}
    </WorkspacePage>
  );
}
