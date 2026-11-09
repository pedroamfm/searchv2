import { ButtonLink } from "@/components/ui";

import { WorkspacePage } from "@/components/page-template";
import { ReportGroupDocuments } from "@/components/reports/report-sections";

export default function WeeklyReportsPage() {
  return (
    <WorkspacePage
      eyebrow="Informes / Semanal"
      title="Informe Semanal"
      description="Captura completa de las 32 categorías: tendencias, rankings, catálogo y visitas."
    >
      <ButtonLink variant="ghost" size="sm" className="mb-6" href="/reports">
        ← Volver a informes
      </ButtonLink>
      <ReportGroupDocuments group="weekly" />
    </WorkspacePage>
  );
}
