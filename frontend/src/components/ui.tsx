import { useEffect, useRef, type ButtonHTMLAttributes, type ReactNode } from "react";

type Variant = "primary" | "secondary" | "danger" | "ghost";

const variants: Record<Variant, string> = {
  primary: "bg-brand text-white hover:bg-brand-strong disabled:bg-line-strong disabled:text-white/90",
  secondary: "bg-surface text-ink border border-line-strong hover:bg-brand-soft disabled:text-muted disabled:hover:bg-surface",
  danger: "bg-danger text-white hover:brightness-90 disabled:opacity-60",
  ghost: "text-brand hover:bg-brand-soft disabled:text-muted",
};

export function Button({
  variant = "primary",
  loading = false,
  className = "",
  children,
  disabled,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; loading?: boolean }) {
  return (
    <button
      {...rest}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition-colors disabled:cursor-not-allowed ${variants[variant]} ${className}`}
    >
      {loading && <Spinner className="size-4" />}
      {children}
    </button>
  );
}

export function Spinner({ className = "size-5", label }: { className?: string; label?: string }) {
  return (
    <svg className={`animate-spin ${className}`} viewBox="0 0 24 24" fill="none" role={label ? "status" : undefined} aria-label={label} aria-hidden={label ? undefined : true}>
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="3" opacity="0.25" />
      <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

const alertStyles = {
  error: "border-danger/40 bg-danger-soft text-danger",
  info: "border-brand/30 bg-brand-soft text-brand-strong",
  warning: "border-signal/40 bg-signal-soft text-signal",
};

export function Alert({
  tone = "error",
  title,
  children,
  action,
}: {
  tone?: keyof typeof alertStyles;
  title?: string;
  children?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div role={tone === "error" ? "alert" : "status"} className={`flex flex-wrap items-start justify-between gap-3 rounded-lg border px-4 py-3 text-sm ${alertStyles[tone]}`}>
      <div className="min-w-0">
        {title && <p className="font-semibold">{title}</p>}
        {children && <div className={title ? "mt-0.5" : ""}>{children}</div>}
      </div>
      {action}
    </div>
  );
}

export function EmptyState({ title, children, action }: { title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="mx-auto flex max-w-md flex-col items-center gap-3 rounded-xl border border-dashed border-line-strong bg-surface px-6 py-12 text-center">
      <h2 className="font-serif text-xl font-semibold">{title}</h2>
      {children && <p className="text-sm leading-relaxed text-muted">{children}</p>}
      {action}
    </div>
  );
}

export function Field({ label, hint, htmlFor, children }: { label: string; hint?: string; htmlFor: string; children: ReactNode }) {
  return (
    <div>
      <label htmlFor={htmlFor} className="block text-sm font-semibold">{label}</label>
      {hint && <p id={`${htmlFor}-hint`} className="mt-0.5 text-sm text-muted">{hint}</p>}
      <div className="mt-1.5">{children}</div>
    </div>
  );
}

export const inputClass =
  "block w-full rounded-lg border border-line-strong bg-surface px-3 py-2.5 text-base text-ink placeholder:text-muted/80 disabled:bg-paper disabled:text-muted";

/** Modal built on the native <dialog>: focus is trapped and Esc closes it. */
export function Dialog({
  open,
  onClose,
  title,
  children,
  footer,
  busy = false,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  footer: ReactNode;
  busy?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (open && !el.open) el.showModal();
    if (!open && el.open) el.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      aria-labelledby="dialog-title"
      onCancel={(e) => {
        e.preventDefault();
        if (!busy) onClose();
      }}
      className="m-auto w-[min(32rem,calc(100vw-2rem))] rounded-xl bg-surface p-0 text-ink shadow-xl"
    >
      <div className="p-6">
        <h2 id="dialog-title" className="font-serif text-xl font-semibold">{title}</h2>
        <div className="mt-3 space-y-3 text-sm leading-relaxed text-muted">{children}</div>
      </div>
      <div className="flex flex-wrap justify-end gap-2 border-t border-line bg-paper px-6 py-4">{footer}</div>
    </dialog>
  );
}
