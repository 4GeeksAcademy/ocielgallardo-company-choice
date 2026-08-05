import { Suspense } from "react";
import { SuppliersWorkspace } from "@/components/SuppliersWorkspace";

function LoadingFallback() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50">
      <p className="text-sm text-slate-600">Cargando directorio de proveedores...</p>
    </div>
  );
}

export default function SuppliersPage() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <SuppliersWorkspace />
    </Suspense>
  );
}