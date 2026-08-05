import { Badge } from "@/components/ui/Badge";
import {
  SUPPLIER_STATUS_BADGE_CLASSES,
  SUPPLIER_STATUS_LABELS,
  type SupplierStatus,
} from "@/types/suppliers";

interface SupplierStatusBadgeProps {
  status: SupplierStatus;
}

export function SupplierStatusBadge({ status }: SupplierStatusBadgeProps) {
  return (
    <Badge className={SUPPLIER_STATUS_BADGE_CLASSES[status]}>
      {SUPPLIER_STATUS_LABELS[status]}
    </Badge>
  );
}