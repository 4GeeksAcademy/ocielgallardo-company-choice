/** UI stock bands: critical < 5, low < 15, healthy >= 15 */
export const STOCK_CRITICAL_BELOW = 5;
export const STOCK_LOW_BELOW = 15;

export type SupplyCategory =
  | "ppe"
  | "wound_care"
  | "diagnostics"
  | "medications"
  | "consumables";

export type SupplyUnit = "box" | "unit" | "pack" | "vial";

export type SupplyCountry = "US" | "UK";

export type ConsumptionType = "clinical_use" | "expiry_waste";

export type OrderType = "inbound" | "outbound";

export interface MedicalSupply {
  id: number;
  name: string;
  sku: string;
  category: string;
  unit: string;
  country: string;
  current_stock: number;
}

export interface MedicalSupplyCreateInput {
  name: string;
  sku: string;
  category: SupplyCategory;
  unit: SupplyUnit;
  country: SupplyCountry;
}

export interface SupplyDelivery {
  id: number;
  supply_id: number;
  quantity: number;
  vendor_name: string;
  clinic_id: number;
  created_at: string;
  user_uuid: string;
}

export interface SupplyDeliveryCreateInput {
  supply_id: number;
  quantity: number;
  vendor_name: string;
  clinic_id: number;
}

export interface SupplyConsumption {
  id: number;
  supply_id: number;
  quantity: number;
  consumption_type: string;
  clinic_id: number;
  created_at: string;
  user_uuid: string;
}

export interface SupplyConsumptionCreateInput {
  supply_id: number;
  quantity: number;
  consumption_type: ConsumptionType;
  clinic_id: number;
}

export interface InventoryOrder {
  order_type: OrderType;
  id: number;
  supply_id: number;
  supply_name: string;
  supply_sku: string;
  quantity: number;
  clinic_id: number;
  created_at: string;
  user_uuid: string;
  vendor_name: string | null;
  consumption_type: string | null;
}

export const SUPPLY_CATEGORY_OPTIONS: Array<{
  value: SupplyCategory;
  label: string;
}> = [
  { value: "ppe", label: "EPI" },
  { value: "wound_care", label: "Curas" },
  { value: "diagnostics", label: "Diagnóstico" },
  { value: "medications", label: "Medicamentos" },
  { value: "consumables", label: "Consumibles" },
];

export const SUPPLY_UNIT_OPTIONS: Array<{
  value: SupplyUnit;
  label: string;
}> = [
  { value: "box", label: "Caja" },
  { value: "unit", label: "Unidad" },
  { value: "pack", label: "Pack" },
  { value: "vial", label: "Vial" },
];

export const SUPPLY_COUNTRY_OPTIONS: Array<{
  value: SupplyCountry;
  label: string;
}> = [
  { value: "US", label: "EE.UU." },
  { value: "UK", label: "Reino Unido" },
];

export const CONSUMPTION_TYPE_OPTIONS: Array<{
  value: ConsumptionType;
  label: string;
}> = [
  { value: "clinical_use", label: "Uso clínico" },
  { value: "expiry_waste", label: "Caducado / desecho" },
];

export const ORDER_TYPE_OPTIONS: Array<{
  value: OrderType;
  label: string;
}> = [
  { value: "inbound", label: "Entrega" },
  { value: "outbound", label: "Consumo" },
];

export const SUPPLY_CATEGORY_LABELS: Record<SupplyCategory, string> =
  Object.fromEntries(
    SUPPLY_CATEGORY_OPTIONS.map((option) => [option.value, option.label])
  ) as Record<SupplyCategory, string>;

export const SUPPLY_UNIT_LABELS: Record<SupplyUnit, string> = Object.fromEntries(
  SUPPLY_UNIT_OPTIONS.map((option) => [option.value, option.label])
) as Record<SupplyUnit, string>;

export const CONSUMPTION_TYPE_LABELS: Record<ConsumptionType, string> =
  Object.fromEntries(
    CONSUMPTION_TYPE_OPTIONS.map((option) => [option.value, option.label])
  ) as Record<ConsumptionType, string>;

export const ORDER_TYPE_LABELS: Record<OrderType, string> = Object.fromEntries(
  ORDER_TYPE_OPTIONS.map((option) => [option.value, option.label])
) as Record<OrderType, string>;

export type StockLevel = "critical" | "low" | "healthy";

export function stockLevelFor(currentStock: number): StockLevel {
  if (currentStock < STOCK_CRITICAL_BELOW) {
    return "critical";
  }
  if (currentStock < STOCK_LOW_BELOW) {
    return "low";
  }
  return "healthy";
}

export const STOCK_LEVEL_BADGE_CLASSES: Record<StockLevel, string> = {
  critical: "bg-red-50 dark:bg-red-950/40 text-red-700 dark:text-red-400 ring-red-600/20",
  low: "bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300 ring-amber-600/20",
  healthy: "bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 ring-emerald-600/20",
};

export const STOCK_LEVEL_LABELS: Record<StockLevel, string> = {
  critical: "Crítico",
  low: "Bajo",
  healthy: "Saludable",
};

export function categoryLabel(category: string): string {
  return (
    SUPPLY_CATEGORY_LABELS[category as SupplyCategory] ?? category
  );
}

export function unitLabel(unit: string): string {
  return SUPPLY_UNIT_LABELS[unit as SupplyUnit] ?? unit;
}

export function countryLabel(country: string): string {
  if (country === "US") return "EE.UU.";
  if (country === "UK") return "Reino Unido";
  return country;
}
