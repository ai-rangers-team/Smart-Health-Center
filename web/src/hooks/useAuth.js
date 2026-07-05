import { useEffect, useState } from "react";
import {
  onAuthStateChanged,
  signInWithPopup,
  signOut as fbSignOut,
} from "firebase/auth";
import { auth, googleProvider } from "../firebase";
import { PREVIEW, previewRole } from "../dev/preview";

/**
 * Auth state + role from Firebase custom claims.
 * role: undefined = still loading / signed out; null = signed in but not provisioned.
 */
export function useAuth() {
  // Dev-only preview harness (VITE_PREVIEW=1): fake identity, no Firebase.
  if (PREVIEW) {
    const role = previewRole();
    return {
      user: { displayName: "Dr. A. Deshmukh", email: "preview@local" },
      role,
      centreId: role === "phc_operator" ? "phc_mulshi" : null,
      districtId: "pune_rural",
      loading: false,
      signIn: () => {},
      signOut: () => {},
    };
  }
  // eslint-disable-next-line react-hooks/rules-of-hooks
  return useRealAuth();
}

function useRealAuth() {
  const [user, setUser] = useState(null);
  const [claims, setClaims] = useState({});
  const [role, setRole] = useState(undefined);
  const [loading, setLoading] = useState(true);

  useEffect(
    () =>
      onAuthStateChanged(auth, async (u) => {
        setUser(u);
        if (u) {
          const res = await u.getIdTokenResult(true);
          setClaims(res.claims);
          setRole(res.claims.role ?? null);
        } else {
          setClaims({});
          setRole(undefined);
        }
        setLoading(false);
      }),
    []
  );

  return {
    user,
    role,
    centreId: claims.centre_id || null,
    districtId: claims.district_id || null,
    loading,
    signIn: () =>
      signInWithPopup(auth, googleProvider).catch((e) => {
        // Benign: user closed the popup / clicked the button twice
        if (
          e?.code !== "auth/cancelled-popup-request" &&
          e?.code !== "auth/popup-closed-by-user"
        )
          throw e;
      }),
    signOut: () => fbSignOut(auth),
  };
}
