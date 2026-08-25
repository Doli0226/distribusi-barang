export const REQUEST_STATUS = {
  pending: { label: "Menunggu", cls: "amber" },
  processed: { label: "Diproses", cls: "blue" },
  approved: { label: "Disetujui", cls: "green" },
  prepared: { label: "Disiapkan", cls: "blue" },
  shipped: { label: "Dikirim", cls: "blue" },
  in_transit: { label: "Dalam perjalanan", cls: "blue" },
  arrived: { label: "Tiba", cls: "green" },
  completed: { label: "Selesai", cls: "green" },
  rejected: { label: "Ditolak", cls: "red" },
};

export const DIST_STATUS = {
  prepared: { label: "Disiapkan", cls: "amber" },
  in_transit: { label: "Dalam pengiriman", cls: "blue" },
  arrived: { label: "Tiba", cls: "green" },
  completed: { label: "Selesai", cls: "green" },
};

export const badgeClass = (status) => {
  if (REQUEST_STATUS[status]) return `badge ${REQUEST_STATUS[status].cls}`;
  if (DIST_STATUS[status]) return `badge ${DIST_STATUS[status].cls}`;
  const m = { "Stok rendah": "red", Aktif: "green", Nonaktif: "gray", available: "green", in_use: "blue", maintenance: "amber" };
  return `badge ${m[status] || "gray"}`;
};

export const statusLabel = (status) =>
  REQUEST_STATUS[status]?.label || DIST_STATUS[status]?.label ||
  ({ available: "Tersedia", in_use: "Digunakan", maintenance: "Perawatan" })[status] || status;

export const formatNumber = (n) => Number(n || 0).toLocaleString("id-ID");
export const formatDate = (d) => (d ? new Date(d).toLocaleDateString("id-ID", { day: "2-digit", month: "short", year: "numeric" }) : "-");
