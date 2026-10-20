export const DEVICE_TYPES = [
  { value: "phone", label: "Phone" },
  { value: "tablet_ipad", label: "Tablet (iPad)" },
  { value: "tablet_android", label: "Tablet (Android)" },
  { value: "smartwatch", label: "Smartwatch" },
];

export const OS_TYPES = [
  { value: "ios", label: "iOS" },
  { value: "android", label: "Android" },
  { value: "watchos", label: "watchOS" },
  { value: "wear_os", label: "Wear OS" },
];

export const STATUSES = [
  { value: "active", label: "Active" },
  { value: "in_repair", label: "In Repair" },
  { value: "retired", label: "Retired" },
  { value: "lost", label: "Lost" },
];

export const AUDIT_STATUSES = [
  { value: "pending_audit", label: "Pending audit" },
  { value: "confirmed", label: "Confirmed" },
  { value: "disputed", label: "Disputed" },
];

export const ROLES = [
  { value: "admin", label: "Admin" },
  { value: "manager", label: "Manager" },
  { value: "viewer", label: "Viewer" },
];

export function labelOf(list, value) {
  return list.find((x) => x.value === value)?.label || value;
}
