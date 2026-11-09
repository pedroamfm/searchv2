import { ButtonLink } from "@/components/ui";

import { WorkspacePage } from "@/components/page-template";
import { ReportGroupDocuments } from "@/components/reports/report-sections";

export default function DailyRankingReportsPage() {
  return (
    <WorkspacePage
      eyebrow="Informes / Ranking Diario"
      title="Ranking Diario"
      description="Posiciones, resultados y primeros lugares observados por categoría en cada captura diaria."
    >
      <ButtonLink variant="ghost" size="sm" className="mb-6" href="/reports">
        ← Volver a informes
      </ButtonLink>
      <ReportGroupDocuments group="rankings" />
    </WorkspacePage>
  );
}
