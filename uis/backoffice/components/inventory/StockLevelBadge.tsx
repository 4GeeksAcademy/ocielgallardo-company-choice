import { Badge } from "@/components/ui/Badge";
import {
  STOCK_LEVEL_BADGE_CLASSES,
  STOCK_LEVEL_LABELS,
  stockLevelFor,
  type StockLevel,
} from "@/types/inventory";

interface StockLevelBadgeProps {
  currentStock: number;
}

export function StockLevelBadge({ currentStock }: StockLevelBadgeProps) {
  // UI-only bands: critical < 5, low < 15, healthy >= 15 (see STOCK_* in types/inventory)
  const level: StockLevel = stockLevelFor(currentStock);

  return (
    <Badge className={STOCK_LEVEL_BADGE_CLASSES[level]}>
      <span className="font-semibold tabular-nums">{currentStock}</span>
      <span className="ml-1.5 font-normal opacity-80">
        {STOCK_LEVEL_LABELS[level]}
      </span>
    </Badge>
  );
}
