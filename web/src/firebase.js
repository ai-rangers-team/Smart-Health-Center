import { initializeApp } from "firebase/app";
import { getAuth, GoogleAuthProvider } from "firebase/auth";
import { initializeFirestore, persistentLocalCache } from "firebase/firestore";

const app = initializeApp({
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
});

export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();

// Offline persistence: operator writes queue offline and sync on reconnect
// (low-connectivity PHCs are a first-class requirement).
export const db = initializeFirestore(app, { localCache: persistentLocalCache() });
