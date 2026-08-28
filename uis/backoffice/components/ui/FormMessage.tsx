import type { ReactNode } from "react";

type FormMessageVariant = "success" | "error" | "info";

const VARIANT_STYLES: Record<FormMessageVariant, string> = {
  success:
    "border-green-200 bg-green-50 text-green-800 dark:border-green-800 dark:bg-green-950/40 dark:text-green-300",
  error:
    "border-red-200 bg-red-50 text-red-800 dark:border-red-800 dark:bg-red-950/40 dark:text-red-300",
  info: "border-slate-200 bg-slate-50 text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200",
};

interface FormMessageProps {
  variant: FormMessageVariant;
  children: ReactNode;
  className?: string;
}

export function FormMessage({
  variant,
  children,
  className = "",
}: FormMessageProps) {
  return (
    <div
      className={`rounded-lg border p-3 text-sm ${VARIANT_STYLES[variant]} ${className}`.trim()}
      role={variant === "error" ? "alert" : "status"}
    >
      {children}
    </div>
  );
}
