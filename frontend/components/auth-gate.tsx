"use client";

import { useQuery } from "@tanstack/react-query";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import { getApi } from "@/lib/api-client";
import { Skeleton } from "@/components/ui";

export type CurrentUser = { email: string; display_name: string; role: "admin" | "viewer" };

export function useCurrentUser() {
  return useQuery({ queryKey: ["current-user"], queryFn: () => getApi<CurrentUser>("/auth/me"), retry: false });
}

export function AuthGate({ children }: Readonly<{ children: React.ReactNode }>) {
  const router = useRouter();
  const pathname = usePathname();
  const user = useCurrentUser();
  useEffect(() => { if (user.isError) router.replace(`/login?next=${encodeURIComponent(pathname)}`); }, [pathname, router, user.isError]);
  if (user.isPending || user.isError) return <main className="p-8"><Skeleton className="h-32 w-full" /></main>;
  return <>{children}</>;
}
