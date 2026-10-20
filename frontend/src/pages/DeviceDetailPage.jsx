import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import api from "../api/client";
import { AUDIT_STATUSES, DEVICE_TYPES, OS_TYPES, STATUSES, labelOf } from "../constants";
import { useAuth } from "../auth/AuthContext";

export default function DeviceDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { canManage, isAdmin } = useAuth();
  const [device, setDevice] = useState(null);
  const [history, setHistory] = useState([]);
  const [audits, setAudits] = useState([]);
  const [tickets, setTickets] = useState([]);
  const [error, setError] = useState("");

  const load = async () => {
    try {
      const [d, h, a, t] = await Promise.all([
        api.get(`/devices/${id}`),
        api.get(`/devices/${id}/history`),
        api.get(`/management/audits?device_id=${id}`),
        api.get(`/management/maintenance`),
      ]);
      setDevice(d.data);
      setHistory(h.data);
      setAudits(a.data);
      setTickets(t.data.filter((tk) => tk.device_id === id));
    } catch (e) {
      setError(e.response?.data?.detail || "Failed to load device");
    }
  };

  useEffect(() => {
    load();
  }, [id]);

  const retire = async () => {
    if (!confirm("Mark this device as retired?")) return;
    await api.patch(`/devices/${id}`, { status: "retired" });
    load();
  };

  const remove = async () => {
    if (!confirm("Permanently delete this device?")) return;
    await api.delete(`/devices/${id}`);
    navigate("/devices");
  };

  const quickReturn = async () => {
    if (!confirm("Confirm device return and check-in back to available inventory?")) return;
    await api.post(`/management/returns/${id}/return`, { condition: "Good", return_notes: "Processed via Device Detail page" });
    load();
  };

  if (error) return <p className="error">{error}</p>;
  if (!device) return <p>Loading…</p>;

  const isAssigned = !!(device.assigned_user_id || device.issued_to);

  return (
    <section className="page">
      <div className="page-head">
        <div>
          <p className="eyebrow">{labelOf(DEVICE_TYPES, device.device_type)}</p>
          <h1>{device.device_name}</h1>
          <p className="lede">{device.device_nickname}</p>
        </div>
        <div className="actions">
          {canManage && isAssigned && (
            <button className="btn primary" type="button" onClick={quickReturn}>
              Process Return
            </button>
          )}
          {canManage && (
            <Link className="btn secondary" to={`/management?tab=maintenance`}>
              + Log Repair
            </Link>
          )}
          {canManage && (
            <Link className="btn secondary" to={`/management?tab=audits`}>
              🛡️ Audit
            </Link>
          )}
          {canManage && (
            <Link className="btn secondary" to={`/devices/${id}/edit`}>
              Edit
            </Link>
          )}
          {canManage && device.status !== "retired" && (
            <button className="btn ghost" type="button" onClick={retire}>
              Retire
            </button>
          )}
          {isAdmin && (
            <button className="btn danger" type="button" onClick={remove}>
              Delete
            </button>
          )}
        </div>
      </div>


      <div className="grid-2">
        <div className="panel">
          <h2>Details</h2>
          <ul className="kv-list">
            <li>
              <span>Status</span>
              <strong>{labelOf(STATUSES, device.status)}</strong>
            </li>
            <li>
              <span>OS</span>
              <strong>
                {labelOf(OS_TYPES, device.os_type)} {device.os_version}
              </strong>
            </li>
            <li>
              <span>Audit status</span>
              <strong>{labelOf(AUDIT_STATUSES, device.audit_status) || device.audit_status || "—"}</strong>
            </li>
            <li>
              <span>Cellular</span>
              <strong>{device.is_cellular ? "Yes" : "No"}</strong>
            </li>
            <li>
              <span>IMEI</span>
              <strong>{device.imei_number || "—"}</strong>
            </li>
            <li>
              <span>Company Serial</span>
              <strong>{device.serial_number}</strong>
            </li>
            <li>
              <span>MAC</span>
              <strong>{device.mac_address}</strong>
            </li>
            <li>
              <span>Company</span>
              <strong>{device.company}</strong>
            </li>
            <li>
              <span>Issued to</span>
              <strong>{device.issued_to || "—"}</strong>
            </li>
            <li>
              <span>Resident location</span>
              <strong>{device.resident_location || "—"}</strong>
            </li>
            <li>
              <span>Division</span>
              <strong>{device.division || "—"}</strong>
            </li>
            <li>
              <span>Project manager</span>
              <strong>{device.project_manager || "—"}</strong>
            </li>
            <li>
              <span>Project name</span>
              <strong>{device.project_name || "—"}</strong>
            </li>
            <li>
              <span>Date of return</span>
              <strong>{device.date_of_return || "—"}</strong>
            </li>
            <li>
              <span>Assigned to</span>
              <strong>{device.assigned_user?.full_name || "Unassigned"}</strong>
            </li>
            <li>
              <span>Purchase date</span>
              <strong>{device.purchase_date || "—"}</strong>
            </li>
          </ul>
        </div>
        <div className="panel">
          <h2>Assignment history</h2>
          {!history.length && <p className="muted">No assignment changes yet.</p>}
          <ul className="timeline">
            {history.map((h) => (
              <li key={h.id}>
                <strong>
                  {h.from_user?.full_name || "Unassigned"} → {h.to_user?.full_name || "Unassigned"}
                </strong>
                <span>
                  by {h.changed_by_user?.full_name || "Unknown"} ·{" "}
                  {new Date(h.created_at).toLocaleString()}
                </span>
                {h.notes && <div className="small-muted">{h.notes}</div>}
              </li>
            ))}
          </ul>

          <h2 style={{ marginTop: "1.5rem" }}>Maintenance & Repairs</h2>
          {!tickets.length && <p className="muted">No maintenance tickets logged for this device.</p>}
          <ul className="timeline">
            {tickets.map((t) => (
              <li key={t.id}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <strong>{t.issue_title}</strong>
                  <span className={`pill status-${t.repair_status}`}>{t.repair_status.replace("_", " ")}</span>
                </div>
                <span>
                  Priority: <strong>{t.priority}</strong> · Vendor: {t.vendor_name || "N/A"} · Cost: ${t.actual_cost || t.estimated_cost || 0}
                </span>
                {t.technician_notes && <div className="small-muted">{t.technician_notes}</div>}
              </li>
            ))}
          </ul>

          <h2 style={{ marginTop: "1.5rem" }}>Audit Logs</h2>
          {!audits.length && <p className="muted">No audit verifications recorded yet.</p>}
          <ul className="timeline">
            {audits.map((a) => (
              <li key={a.id}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <strong>Cycle: {a.audit_cycle}</strong>
                  <span className={`pill audit-${a.physical_status}`}>{a.physical_status}</span>
                </div>
                <span>
                  Auditor: {a.auditor?.full_name || "Auditor"} · Verified Location: {a.verified_location || "HQ"}
                </span>
                {a.notes && <div className="small-muted">{a.notes}</div>}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}

