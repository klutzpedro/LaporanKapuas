import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "@/lib/auth";
import ErrorBoundary from "@/components/ErrorBoundary";
import LoginPage from "@/pages/Login";
import AppLayout from "@/components/AppLayout";
import Dashboard from "@/pages/Dashboard";
import SummaryPage from "@/pages/Summary";
import HistoryPage from "@/pages/History";
import TimLid from "@/pages/teams/TimLid";
import TimKontra from "@/pages/teams/TimKontra";
import TimGal from "@/pages/teams/TimGal";
import TimMedmon from "@/pages/teams/TimMedmon";
import TimGeoint from "@/pages/teams/TimGeoint";
import Piket from "@/pages/teams/Piket";
import AdminUsers from "@/pages/AdminUsers";

function RoleGate({ roles, children }) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== "admin" && !roles.includes(user.role)) return <Navigate to="/" replace />;
  return children;
}

export default function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route element={<AppLayout />}>
              <Route path="/" element={<Dashboard />} />
              <Route path="/summary" element={<RoleGate roles={["piket"]}><SummaryPage /></RoleGate>} />
              <Route path="/history" element={<RoleGate roles={["piket"]}><HistoryPage /></RoleGate>} />
              <Route path="/team/lid" element={<RoleGate roles={["tim_lid"]}><TimLid /></RoleGate>} />
              <Route path="/team/kontra" element={<RoleGate roles={["tim_kontra"]}><TimKontra /></RoleGate>} />
              <Route path="/team/gal" element={<RoleGate roles={["tim_gal"]}><TimGal /></RoleGate>} />
              <Route path="/team/medmon" element={<RoleGate roles={["tim_medmon"]}><TimMedmon /></RoleGate>} />
              <Route path="/team/geoint" element={<RoleGate roles={["tim_geoint"]}><TimGeoint /></RoleGate>} />
              <Route path="/team/piket" element={<RoleGate roles={["piket"]}><Piket /></RoleGate>} />
              <Route path="/admin/users" element={<RoleGate roles={[]}><AdminUsers /></RoleGate>} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ErrorBoundary>
  );
}
