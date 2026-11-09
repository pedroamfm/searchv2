import { AppShell } from "@/components/app-shell";
import type { Metadata } from "next";

import { QueryProvider } from "@/components/query-provider";

import "./globals.css";

export const metadata: Metadata = {
  title: { default: "Product Radar", template: "%s · Product Radar" },
  description: "Inteligencia de productos y señales de mercado",
  applicationName: "Product Radar",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="es">
      <body>
        <QueryProvider><AppShell>{children}</AppShell></QueryProvider>
      </body>
    </html>
  );
}
