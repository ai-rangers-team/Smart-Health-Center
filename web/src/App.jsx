import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./hooks/useAuth";
import Login from "./pages/Login";
import NotProvisioned from "./pages/NotProvisioned";
import Dashboard from "./pages/Dashboard";
import CentreDetail from "./pages/CentreDetail";
import MyCentre from "./pages/MyCentre";
import OnboardCentre from "./pages/OnboardCentre";

export default function App() {
  const { user, role, loading, signIn, signOut } = useAuth();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-teal">
        Loading…
      </div>
    );
  }
  if (!user) return <Login onSignIn={signIn} />;
  if (role === null) return <NotProvisioned email={user.email} onSignOut={signOut} />;

  if (role === "district_admin") {
    return (
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/centre/:centreId" element={<CentreDetail />} />
        <Route path="/onboard-centre" element={<OnboardCentre />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    );
  }
  if (role === "phc_operator") {
    return (
      <Routes>
        <Route path="/" element={<MyCentre />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    );
  }
  return <NotProvisioned email={user.email} onSignOut={signOut} />;
}
