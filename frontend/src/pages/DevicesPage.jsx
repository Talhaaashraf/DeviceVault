import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api/client";
import { AUDIT_STATUSES, DEVICE_TYPES, OS_TYPES, STATUSES, labelOf } from "../constants";
import { useAuth } from "../auth/AuthContext";

const emptyFilters = {
  q: "",
  device_type: "",
  os_type: "",
  company: "",
  status: "",
  unassigned: "",
};

export default function DevicesPage() {
  const { canManage } = useAuth();
  const [filters, setFilters] = useState(emptyFilters);
  const [devices, setDevices] = useState([]);
  const [error, setError] = useState("");
  const [importMsg, setImportMsg] = useState("");
  const [importing, setImporting] = useState(false);
  const [loading, setLoading] = useState(true);
  const fileRef = useRef(null);

  const load = async (next = filters) => {
    setLoading(true);
    setError("");
    try {
      const params = {};
      Object.entries(next).forEach(([k, v]) => {
        if (v !== "" && v !== null && v !== undefined) params[k] = v;
      });
      if (params.unassigned === "true") params.unassigned = true;
      else delete params.unassigned;
      const { data } = await api.get("/devices", { params });
      setDevices(data);
    } catch (e) {
      setError(e.response?.data?.detail || "Failed to load devices");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const onChange = (e) => {
    const { name, value } = e.target;
    setFilters((f) => ({ ...f, [name]: value }));
  };

  const onImport = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImporting(true);
    setImportMsg("");
    setError("");
    try {
      const body = new FormData();
      body.append("file", file);
      const { data } = await api.post("/devices/import", body, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const failNote = data.failed
        ? ` ${data.failed} row(s) failed: ${data.errors
            .slice(0, 3)
            .map((x) => `row ${x.row} (${x.error})`)
            .join("; ")}`
        : "";
      setImportMsg(`Imported ${data.created} device(s).${failNote}`);
      await load();
    } catch (err) {
      setError(err.response?.data?.detail || "CSV import failed");
    } finally {
      setImporting(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  return (
    <section className="page">
      <div className="page-head">
        <div>
          <h1>Devices</h1>
          <p className="lede">Search, filter, or import your fleet from a CSV file.</p>
        </div>
        {canManage && (
          <div className="actions">
            <label className="btn secondary file-btn">
              {importing ? "Importing…" : "Import CSV"}
              <input
                ref={fileRef}
                type="file"
                accept=".csv,text/csv"
                hidden
                disabled={importing}
                onChange={onImport}
              />
            </label>
            <a className="btn ghost" href="/sample-devices.csv" download>
              CSV template
            </a>
            <Link className="btn primary" to="/devices/new">
              Add device
            </Link>
          </div>
        )}
      </div>

      {canManage && (
        <div className="panel import-hint">
          <strong>CSV columns:</strong> device_name, device_nickname, device_type, os_type,
          os_version, is_cellular, imei_number, serial_number, mac_address, company, status,
          audit_status, resident_location, division, issued_to, project_manager, project_name,
          date_of_return, purchase_date, assigned_user_email
          <div className="muted">
            device_type: phone | tablet_ipad | tablet_android | smartwatch · os_type: ios | android |
            watchos | wear_os · is_cellular: true/false · audit_status: pending_audit | confirmed |
            disputed · date_of_return / purchase_date: YYYY-MM-DD
          </div>
        </div>
      )}

      <form
        className="filters"
        onSubmit={(e) => {
          e.preventDefault();
          load(filters);
        }}
      >
        <input name="q" placeholder="Search name, serial, IMEI…" value={filters.q} onChange={onChange} />
        <select name="device_type" value={filters.device_type} onChange={onChange}>
          <option value="">All types</option>
          {DEVICE_TYPES.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>
        <select name="os_type" value={filters.os_type} onChange={onChange}>
          <option value="">All OS</option>
          {OS_TYPES.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <select name="status" value={filters.status} onChange={onChange}>
          <option value="">All statuses</option>
          {STATUSES.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
        <input name="company" placeholder="Company" value={filters.company} onChange={onChange} />
        <select name="unassigned" value={filters.unassigned} onChange={onChange}>
          <option value="">Assignment</option>
          <option value="true">Unassigned only</option>
        </select>
        <button className="btn secondary" type="submit">
          Apply
        </button>
      </form>

      {error && <p className="error">{error}</p>}
      {importMsg && <p className="success">{importMsg}</p>}
      {loading ? (
        <p>Loading…</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Name / AKA</th>
                <th>Type</th>
                <th>OS</th>
                <th>OS Version</th>
                <th>Company Serial</th>
                <th>IMEI</th>
                <th>Issued</th>
                <th>Location</th>
                <th>Division</th>
                <th>Audit</th>
                <th>Project Manager</th>
                <th>Project Name</th>
                <th>Date of Return</th>
                <th>Status</th>
                <th>Assigned</th>
                <th>Company</th>
              </tr>
            </thead>
            <tbody>
              {devices.map((d) => (
                <tr key={d.id}>
                  <td>
                    <Link to={`/devices/${d.id}`}>{d.device_name}</Link>
                  </td>
                  <td>
                    <div className="muted">{d.device_nickname || "—"}</div>
                  </td>
                  <td>{labelOf(DEVICE_TYPES, d.device_type)}</td>
                  <td>{labelOf(OS_TYPES, d.os_type)}</td>
                  <td>{d.os_version || "—"}</td>
                  <td>{d.serial_number || "—"}</td>
                  <td>
                    <span className="muted">{d.imei_number || "—"}</span>
                  </td>
                  <td>{d.issued_to || "—"}</td>
                  <td>
                    <span className="muted">{d.resident_location || "—"}</span>
                  </td>
                  <td>{d.division || "—"}</td>
                  <td>{labelOf(AUDIT_STATUSES, d.audit_status) || d.audit_status || "—"}</td>
                  <td>
                    <span className="muted">{d.project_manager || "—"}</span>
                  </td>
                  <td>{d.project_name || "—"}</td>
                  <td>{d.date_of_return || "—"}</td>
                  <td>
                    <span className={`pill status-${d.status}`}>{labelOf(STATUSES, d.status)}</span>
                  </td>
                  <td>{d.assigned_user?.full_name || "—"}</td>
                  <td>{d.company}</td>
                </tr>
              ))}
              {!devices.length && (
                <tr>
                  <td colSpan={17}>No devices match these filters.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
