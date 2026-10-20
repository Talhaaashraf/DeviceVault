import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api/client";
import {
  DEVICE_TYPES,
  OS_TYPES,
  STATUSES,
  labelOf,
} from "../constants";
import { useAuth } from "../auth/AuthContext";

const freshnessGroups = ["Latest", "Recent", "Outdated", "Unknown"];

export default function DashboardPage() {
  const { canManage } = useAuth();
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get("/dashboard/summary")
      .then((r) => setSummary(r.data))
      .catch((e) => setError(e.response?.data?.detail || "Failed to load dashboard"));
  }, []);

  if (error) return <p className="error">{error}</p>;
  if (!summary) return <p>Loading dashboard…</p>;

  const allocatedDevices = summary.allocated_devices;
  const pendingAuditCount = summary.by_audit_status?.pending_audit || 0;
  const lostCount = summary.by_status?.lost || 0;
  const projectRows = Object.entries(summary.by_project).sort((a, b) => b[1] - a[1]);
  const categoryEntries = Object.entries(summary.by_category);
  const categoryMax = Math.max(...categoryEntries.map(([, value]) => value), 1);

  return (
    <section className="page">
      <div className="page-head">
        <div>
          <h1>Dashboard</h1>
          <p className="lede">Inventory at a glance across status and platforms.</p>
        </div>
        {canManage && (
          <Link className="btn primary" to="/devices/new">
            Add device
          </Link>
        )}
      </div>

      <div className="stat-row">
        <div className="stat">
          <span>Total devices</span>
          <strong>{summary.total_devices}</strong>
        </div>
        <div className="stat">
          <span>In stock</span>
          <strong>{summary.in_stock.count}</strong>
        </div>
        <div className="stat">
          <span>Currently allocated</span>
          <strong>{allocatedDevices}</strong>
        </div>
        <div className="stat">
          <span>Pending audit</span>
          <strong>{pendingAuditCount}</strong>
        </div>
        <div className="stat">
          <span>Lost / stolen</span>
          <strong>{lostCount}</strong>
        </div>
      </div>

      <div className="stat-row">
        <div className="stat">
          <span>Utilization</span>
          <strong>{summary.utilization_rate}%</strong>
        </div>
        <div className="stat">
          <span>Pending requests</span>
          <strong>{summary.pending_requests_count}</strong>
        </div>
        <div className="stat">
          <span>Overdue returns</span>
          <strong>{summary.overdue_returns_count}</strong>
        </div>
        <div className="stat">
          <span>Active repairs</span>
          <strong>{summary.active_repairs_count}</strong>
        </div>
        <div className="stat">
          <span>Audit this quarter</span>
          <strong>{summary.audit_completion_percentage}%</strong>
        </div>
      </div>

      {summary.urgent_alerts.length > 0 && (
        <div className="panel">
          <h2>Needs attention</h2>
          <ul className="kv-list">
            {summary.urgent_alerts.map((alert) => (
              <li key={`${alert.type}-${alert.id}`}>
                <div>
                  <strong>{alert.title}</strong>
                  <div className="muted">{alert.subtitle}</div>
                </div>
                <Link className="btn ghost" to={alert.type === "overdue" ? `/devices/${alert.id}` : "/management"}>
                  {alert.badge}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="grid-2">
        <div className="panel">
          <h2>Devices by category</h2>
          <ul className="kv-list">
            {categoryEntries.map(([category, count]) => (
              <li key={category}>
                <span>{category}</span>
                <div style={{ flex: 1, marginLeft: "1rem", minWidth: 0 }}>
                  <div
                    style={{
                      height: 10,
                      borderRadius: 999,
                      background: "rgba(20,32,26,0.08)",
                      overflow: "hidden",
                    }}
                  >
                    <div
                      style={{
                        width: `${Math.round((count / categoryMax) * 100)}%`,
                        height: "100%",
                        background: "var(--accent)",
                      }}
                    />
                  </div>
                </div>
                <strong>{count}</strong>
              </li>
            ))}
          </ul>
        </div>

        <div className="panel">
          <h2>OS freshness</h2>
          <table>
            <thead>
              <tr>
                <th>OS</th>
                {freshnessGroups.map((group) => (
                  <th key={group}>{group}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {OS_TYPES.map((os) => (
                <tr key={os.value}>
                  <td>{os.label}</td>
                  {freshnessGroups.map((group) => (
                    <td key={group}>{summary.by_os_freshness?.[os.value]?.[group] || 0}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="grid-2">
        <div className="panel">
          <h2>Devices by project</h2>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Project</th>
                  <th>Count</th>
                </tr>
              </thead>
              <tbody>
                {projectRows.map(([projectName, count]) => (
                  <tr key={projectName}>
                    <td>{projectName}</td>
                    <td>{count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="panel">
          <h2>Latest models</h2>
          <ul className="kv-list">
            {summary.latest_models.length ? (
              summary.latest_models.map((device) => (
                <li key={device.id}>
                  <div>
                    <strong>{device.device_name}</strong>
                    <div className="muted">
                      {device.device_nickname} · {labelOf(OS_TYPES, device.os_type)}
                    </div>
                  </div>
                  <span>{device.issued_to || "Unassigned"}</span>
                </li>
              ))
            ) : (
              <li>
                <span className="muted">No latest models marked yet.</span>
              </li>
            )}
          </ul>
        </div>
      </div>

      <div className="panel">
        <h2>In stock — Available to allocate</h2>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Device</th>
                <th>Type</th>
                <th>OS</th>
                <th>Serial</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {summary.in_stock.list.map((device) => (
                <tr key={device.id}>
                  <td>{device.device_name}</td>
                  <td>{labelOf(DEVICE_TYPES, device.device_type)}</td>
                  <td>{labelOf(OS_TYPES, device.os_type)}</td>
                  <td>{device.serial_number}</td>
                  <td>
                    <Link className="btn secondary" to={`/devices/${device.id}`}>
                      Allocate
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
