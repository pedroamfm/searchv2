"use client";

import { WorkspacePage } from "@/components/page-template";
import { ReportsIndex } from "@/components/reports/report-sections";

export default function ReportsPage() {
  return <WorkspacePage eyebrow="Informes" title="Centro de informes" description="Selecciona un tipo de informe para consultar sus documentos y detalles."><ReportsIndex /></WorkspacePage>;
}
