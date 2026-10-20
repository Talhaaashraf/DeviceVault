import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export default function Layout() {
  const { user, logout, isAdmin } = useAuth();
  const navigate = useNavigate();

  const onLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand-block">
          <span className="brand">DeviceVault</span>
          <span className="brand-sub">Mobile device management</span>
        </div>
        <nav className="nav">
          <NavLink to="/" end>
            Dashboard
          </NavLink>
          <NavLink to="/devices">Devices</NavLink>
          <NavLink to="/management">Management</NavLink>
          {isAdmin && <NavLink to="/users">Users</NavLink>}
        </nav>
        <div className="user-chip">
          <div>
            <strong>{user?.full_name}</strong>
            <span>{user?.role}</span>
          </div>
          <button type="button" className="btn ghost" onClick={onLogout}>
            Log out
          </button>
        </div>
      </header>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
