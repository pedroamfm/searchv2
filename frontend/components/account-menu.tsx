"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { CurrentUser } from "@/components/auth-gate";
import { Button } from "@/components/ui";
import { postApi } from "@/lib/api-client";

function csrfToken(): string | undefined {
  return document.cookie
    .split("; ")
    .find((item) => item.startsWith("product_radar_csrf="))
    ?.split("=")[1];
}

export function AccountMenu({ user }: Readonly<{ user: CurrentUser }>) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const logout = useMutation({
    mutationFn: () => postApi<void>("/auth/logout", undefined, csrfToken()),
    onSuccess: () => {
      queryClient.clear();
      router.replace("/login");
    },
  });
  return (
    <div className="border-t border-[var(--line)] p-4">
      <p className="truncate text-sm font-medium">{user.display_name}</p>
      <p className="mt-1 truncate text-xs text-[var(--muted)]">{user.email}</p>
      <Button
        variant="ghost"
        size="sm"
        className="mt-3"
        loading={logout.isPending}
        loadingLabel="Cerrando…"
        onClick={() => logout.mutate()}
        type="button"
      >
        Cerrar sesión
      </Button>
    </div>
  );
}
