export interface NavLinkItem {
  href: string;
  label: string;
}

export interface NavGroup {
  id: string;
  label: string;
  /** When set and items is empty/omitted, the group label itself is a link. */
  href?: string;
  items: NavLinkItem[];
}

export const DASHBOARD_HREF = "/" as const;

export const WORK_NAV_GROUPS: NavGroup[] = [
  {
    id: "incidents",
    label: "Incidents",
    items: [
      { href: "/incidents", label: "List" },
      { href: "/incidents/new", label: "New incident" },
      { href: "/incidents/summary", label: "Summary" },
      { href: "/incidents/analyze", label: "Analyze CSV" },
    ],
  },
  {
    id: "suppliers",
    label: "Suppliers",
    href: "/suppliers",
    items: [],
  },
  {
    id: "inventory",
    label: "Inventory",
    items: [
      { href: "/inventory/products", label: "Suministros" },
      { href: "/inventory/orders/inbound", label: "Registrar entrega" },
      { href: "/inventory/orders/outbound", label: "Registrar consumo" },
      { href: "/inventory/orders", label: "Historial de órdenes" },
    ],
  },
  {
    id: "people-talent",
    label: "People & Talent",
    href: "/applications",
    items: [],
  },
];

export const ACCOUNT_MENU_ITEMS: NavLinkItem[] = [
  { href: "/account/profile", label: "Profile" },
  { href: "/account/change-password", label: "Change password" },
];

export function isPathActive(pathname: string, href: string): boolean {
  if (href === "/") {
    return pathname === "/";
  }
  if (href === "/incidents") {
    return pathname === "/incidents";
  }
  if (href === "/inventory/orders") {
    return pathname === "/inventory/orders";
  }
  if (href === "/applications") {
    return pathname === "/applications" || pathname.startsWith("/candidates/");
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function isGroupActive(pathname: string, group: NavGroup): boolean {
  if (group.href && isPathActive(pathname, group.href)) {
    return true;
  }
  return group.items.some((item) => isPathActive(pathname, item.href));
}

export function linkClassName(active: boolean): string {
  return active
    ? "bg-blue-50 text-blue-700 font-semibold dark:bg-blue-950/60 dark:text-blue-300"
    : "text-slate-700 hover:bg-slate-100 hover:text-blue-700 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-blue-300";
}
