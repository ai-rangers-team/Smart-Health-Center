import { useEffect, useState } from "react";
import {
  onAuthStateChanged,
  signInWithPopup,
  signOut as fbSignOut,
} from "firebase/auth";
import { auth, googleProvider } from "../firebase";

/**
 * Auth state + role from Firebase custom claims.
 * role: undefined = still loading / signed out; null = signed in but not provisioned.
 */
export function useAuth() {
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
    signIn: () => signInWithPopup(auth, googleProvider),
    signOut: () => fbSignOut(auth),
  };
}
