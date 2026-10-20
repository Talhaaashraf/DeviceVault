import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth/AuthContext";
import Layout from "./components/Layout";
import DashboardPage from "./pages/DashboardPage";
import DeviceDetailPage from "./pages/DeviceDetailPage";
import DeviceFormPage from "./pages/DeviceFormPage";
import DevicesPage from "./pages/DevicesPage";
import LoginPage from "./pages/LoginPage";
import ManagementPage from "./pages/ManagementPage";
import UsersPage from "./pages/UsersPage";


function Protected({ children, roles }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="page-center">Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/" replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <Protected>
            <Layout />
          </Protected>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="devices" element={<DevicesPage />} />
        <Route
          path="devices/new"
          element={
            <Protected roles={["admin", "manager"]}>
              <DeviceFormPage />
            </Protected>
          }
        />
        <Route path="devices/:id" element={<DeviceDetailPage />} />
        <Route
          path="devices/:id/edit"
          element={
            <Protected roles={["admin", "manager"]}>
              <DeviceFormPage />
            </Protected>
          }
        />
        <Route path="management" element={<ManagementPage />} />
        <Route
          path="users"
          element={
            <Protected roles={["admin"]}>
              <UsersPage />
            </Protected>
          }
        />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
