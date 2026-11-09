import { ButtonLink } from "@/components/ui";

import { WorkspacePage } from "@/components/page-template";
import { ReportGroupDocuments } from "@/components/reports/report-sections";

export default function DailyCatalogReportsPage() {
  return (
    <WorkspacePage
      eyebrow="Informes / Catálogo Diario"
      title="Catálogo Diario"
      description="Productos priorizados, ofertas, precios y visitas observadas durante la actualización diaria."
    >
      <ButtonLink variant="ghost" size="sm" className="mb-6" href="/reports">
        ← Volver a informes
      </ButtonLink>
      <ReportGroupDocuments group="catalog" />
    </WorkspacePage>
  );
}
