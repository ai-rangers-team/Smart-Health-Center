/** Dev-only preview mode: VITE_PREVIEW=1 + ?role=admin|operator. */
export const PREVIEW =
  import.meta.env.DEV && import.meta.env.VITE_PREVIEW === "1";

export function previewRole() {
  const q = new URLSearchParams(window.location.search).get("role");
  if (q === "operator") return "phc_operator";
  if (q === "super") return "super_admin";
  return "district_admin";
}
