"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { Button } from "@/components/ui";

export function HistoryPanel({
  title,
  description,
  opener,
  onClose,
  children,
}: Readonly<{
  title: string;
  description: string;
  opener: HTMLElement | null;
  onClose: () => void;
  children: ReactNode;
}>) {
  const backdrop = useRef<HTMLDivElement>(null);
  const panel = useRef<HTMLDivElement>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    const background = Array.from(document.body.children).filter(
      (element): element is HTMLElement =>
        element instanceof HTMLElement && element !== backdrop.current,
    );
    const previous = background.map((element) => element.inert);
    background.forEach((element) => {
      element.inert = true;
    });
    const overflow = document.body.style.overflow;
    const padding = document.body.style.paddingRight;
    const scrollbar = window.innerWidth - document.documentElement.clientWidth;
    document.body.style.overflow = "hidden";
    if (scrollbar > 0) document.body.style.paddingRight = `${scrollbar}px`;
    heading.current?.focus({ preventScroll: true });
    return () => {
      background.forEach((element, index) => {
        element.inert = previous[index];
      });
      document.body.style.overflow = overflow;
      document.body.style.paddingRight = padding;
      if (opener?.isConnected) opener.focus({ preventScroll: true });
    };
  }, [opener]);
  return createPortal(
    <div
      ref={backdrop}
      className="history-backdrop"
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
      onKeyDown={(event) => {
        if (event.key === "Escape") {
          event.preventDefault();
          event.stopPropagation();
          onClose();
        }
        if (event.key !== "Tab") return;
        const controls = Array.from(
          panel.current?.querySelectorAll<HTMLElement>(
            'button:not(:disabled), a[href], input:not(:disabled), select:not(:disabled), [tabindex="0"]',
          ) || [],
        );
        const first = controls[0];
        const last = controls[controls.length - 1];
        if (
          event.shiftKey &&
          (document.activeElement === first ||
            document.activeElement === heading.current)
        ) {
          event.preventDefault();
          last?.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first?.focus();
        }
      }}
    >
      <div
        ref={panel}
        className="history-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="history-title"
        aria-describedby="history-description"
      >
        <div className="flex items-start justify-between gap-4">
          <h2
            ref={heading}
            id="history-title"
            tabIndex={-1}
            className="min-w-0 break-words text-xl font-semibold"
          >
            {title}
          </h2>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            aria-label="Cerrar historial"
          >
            Cerrar
          </Button>
        </div>
        <p
          id="history-description"
          className="mt-3 text-sm leading-6 text-[var(--muted)]"
        >
          {description}
        </p>
        <div className="mt-6">{children}</div>
      </div>
    </div>,
    document.body,
  );
}
