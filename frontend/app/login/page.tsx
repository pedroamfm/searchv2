"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { ApiClientError, postApi } from "@/lib/api-client";
import { Button, ErrorState } from "@/components/ui";

type LoginResult = {
  email: string;
  display_name: string;
  role: "admin" | "viewer";
  csrf_token: string;
};

export default function LoginPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const login = useMutation({
    mutationFn: () => postApi<LoginResult>("/auth/login", { email, password }),
    onSuccess: async (user) => {
      await queryClient.setQueryData(["current-user"], user);
      router.replace("/");
    },
  });
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    login.mutate();
  };
  return (
    <main className="flex min-h-screen items-center justify-center p-5">
      <section className="w-full max-w-md rounded-2xl border border-[var(--line)] bg-[var(--surface)] p-6 sm:p-8">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--accent)]">
          Product Radar
        </p>
        <h1 className="mt-3 text-3xl font-semibold">Iniciar sesión</h1>
        <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
          Acceso exclusivo para usuarios autorizados.
        </p>
        <form className="mt-7 space-y-4" onSubmit={submit}>
          <label className="block text-sm font-medium">
            Correo
            <input
              className="mt-2 w-full rounded-lg border border-[var(--line)] bg-[var(--background)] px-3 py-2.5"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </label>
          <label className="block text-sm font-medium">
            Contraseña
            <input
              className="mt-2 w-full rounded-lg border border-[var(--line)] bg-[var(--background)] px-3 py-2.5"
              type="password"
              autoComplete="current-password"
              minLength={12}
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>
          <Button
            variant="primary"
            className="w-full"
            loading={login.isPending}
            loadingLabel="Validando…"
            type="submit"
          >
            Ingresar
          </Button>
        </form>
        {login.isError ? (
          <div className="mt-4">
            <ErrorState
              message={
                login.error instanceof ApiClientError
                  ? login.error.message
                  : "No fue posible iniciar sesión."
              }
            />
          </div>
        ) : null}
      </section>
    </main>
  );
}
