"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { NAVIGATION_ITEMS } from "@/lib/navigation";
import { AccountMenu } from "@/components/account-menu";
import { AuthGate, useCurrentUser } from "@/components/auth-gate";

export function AppShell({ children }: Readonly<{ children: ReactNode }>) {
  const pathname = usePathname();
  const user = useCurrentUser();
  if (pathname === "/login") return <>{children}</>;

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[15.5rem_1fr]">
      <a className="skip-link" href="#main-content">
        Saltar al contenido principal
      </a>
      <aside className="border-b border-[var(--line)] bg-[var(--surface)] lg:min-h-screen lg:border-r lg:border-b-0">
        <div className="flex items-center justify-between px-5 py-4 lg:block lg:px-6 lg:py-7">
          <Link className="text-lg font-semibold tracking-[-0.03em]" href="/">
            Product Radar
          </Link>
          <span className="text-xs font-medium uppercase tracking-[0.16em] text-[var(--accent)]">
            v0.1
          </span>
        </div>
        <nav
          aria-label="Navegación principal"
          className="overflow-x-auto px-3 pb-4 lg:px-4"
        >
          <ul className="flex min-w-max gap-1 lg:block">
            {NAVIGATION_ITEMS.map((item) => {
              const active =
                item.href === "/"
                  ? pathname === "/"
                  : pathname.startsWith(item.href);
              return (
                <li key={item.href}>
                  <Link
                    aria-current={active ? "page" : undefined}
                    className="nav-link"
                    href={item.href}
                  >
                    {item.title}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
        {user.data ? <AccountMenu user={user.data} /> : null}
      </aside>
      <div className="min-w-0">
        <AuthGate>{children}</AuthGate>
      </div>
    </div>
  );
}
