import { badgeClass, statusLabel } from "@/constants/status";

export default function StatusBadge({ status, label }) {
  return <span className={badgeClass(status)} data-testid={`status-${status}`}>{label || statusLabel(status)}</span>;
}
