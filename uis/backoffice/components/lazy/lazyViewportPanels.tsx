"use client";

import { createLazyViewportPanel } from "@/components/ui/createLazyViewportPanel";

export const ApplicationsWorkspacePanel = createLazyViewportPanel(
  () =>
    import("@/components/ApplicationsWorkspace").then((mod) => ({
      default: mod.ApplicationsWorkspace,
    })),
  {
    minHeight: "60vh",
    label: "Loading application pipeline…",
  },
);

export const SuppliersWorkspacePanel = createLazyViewportPanel(
  () =>
    import("@/components/SuppliersWorkspace").then((mod) => ({
      default: mod.SuppliersWorkspace,
    })),
  {
    minHeight: "60vh",
    label: "Loading supplier directory…",
  },
);

export const MedicalSuppliesListPanel = createLazyViewportPanel(
  () =>
    import("@/components/inventory/MedicalSuppliesList").then((mod) => ({
      default: mod.MedicalSuppliesList,
    })),
  {
    minHeight: "50vh",
    label: "Loading medical supplies…",
  },
);

export const InventoryOrdersListPanel = createLazyViewportPanel(
  () =>
    import("@/components/inventory/InventoryOrdersList").then((mod) => ({
      default: mod.InventoryOrdersList,
    })),
  {
    minHeight: 400,
    label: "Loading order history…",
  },
);

export const InboundOrderFormPanel = createLazyViewportPanel(
  () =>
    import("@/components/inventory/InboundOrderForm").then((mod) => ({
      default: mod.InboundOrderForm,
    })),
  {
    minHeight: 360,
    label: "Loading delivery form…",
  },
);

export const OutboundOrderFormPanel = createLazyViewportPanel(
  () =>
    import("@/components/inventory/OutboundOrderForm").then((mod) => ({
      default: mod.OutboundOrderForm,
    })),
  {
    minHeight: 360,
    label: "Loading usage form…",
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
    label: "Loading application…",
  },
);
