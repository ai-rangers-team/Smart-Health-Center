/** Dev-only preview mode: VITE_PREVIEW=1 + ?role=admin|operator. */
export const PREVIEW =
  import.meta.env.DEV && import.meta.env.VITE_PREVIEW === "1";

export function previewRole() {
  const q = new URLSearchParams(window.location.search).get("role");
  return q === "operator" ? "phc_operator" : "district_admin";
}
