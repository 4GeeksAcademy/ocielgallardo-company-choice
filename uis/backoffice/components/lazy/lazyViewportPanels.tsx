"use client";

import { createLazyViewportPanel } from "@/components/ui/createLazyViewportPanel";

export const ApplicationsWorkspacePanel = createLazyViewportPanel(
  () =>
    import("@/components/ApplicationsWorkspace").then((mod) => ({
      default: mod.ApplicationsWorkspace,
    })),
  {
    minHeight: "60vh",
    label: "Cargando pipeline de candidaturas…",
  },
);

export const SuppliersWorkspacePanel = createLazyViewportPanel(
  () =>
    import("@/components/SuppliersWorkspace").then((mod) => ({
      default: mod.SuppliersWorkspace,
    })),
  {
    minHeight: "60vh",
    label: "Cargando directorio de proveedores…",
  },
);

export const MedicalSuppliesListPanel = createLazyViewportPanel(
  () =>
    import("@/components/inventory/MedicalSuppliesList").then((mod) => ({
      default: mod.MedicalSuppliesList,
    })),
  {
    minHeight: "50vh",
    label: "Cargando suministros médicos…",
  },
);

export const InventoryOrdersListPanel = createLazyViewportPanel(
  () =>
    import("@/components/inventory/InventoryOrdersList").then((mod) => ({
      default: mod.InventoryOrdersList,
    })),
  {
    minHeight: 400,
    label: "Cargando historial de órdenes…",
  },
);

export const InboundOrderFormPanel = createLazyViewportPanel(
  () =>
    import("@/components/inventory/InboundOrderForm").then((mod) => ({
      default: mod.InboundOrderForm,
    })),
  {
    minHeight: 360,
    label: "Cargando formulario de entrega…",
  },
);

export const OutboundOrderFormPanel = createLazyViewportPanel(
  () =>
    import("@/components/inventory/OutboundOrderForm").then((mod) => ({
      default: mod.OutboundOrderForm,
    })),
  {
    minHeight: 360,
    label: "Cargando formulario de consumo…",
  },
);

export const CandidateDetailWorkspacePanel = createLazyViewportPanel(
  () =>
    import("@/components/candidates/CandidateDetailWorkspace").then((mod) => ({
      default: mod.CandidateDetailWorkspace as typeof mod.CandidateDetailWorkspace &
        import("react").ComponentType<Record<string, unknown>>,
    })),
  {
    minHeight: "60vh",
    label: "Cargando candidatura…",
  },
);
