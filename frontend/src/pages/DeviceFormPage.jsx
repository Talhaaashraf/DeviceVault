import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import api from "../api/client";
import { AUDIT_STATUSES, DEVICE_TYPES, OS_TYPES, STATUSES } from "../constants";

const blank = {
  device_name: "",
  device_nickname: "",
  device_type: "phone",
  os_type: "ios",
  os_version: "",
  audit_status: "pending_audit",
  resident_location: "",
  division: "",
  issued_to: "",
  issued_to_email: "",
  project_manager: "",
  project_name: "",
  is_latest_model: false,
  date_of_return: "",
  is_cellular: true,
  imei_number: "",
  serial_number: "",
  mac_address: "",
  company: "",
  assigned_user_id: "",
  status: "active",
  purchase_date: "",
};

export default function DeviceFormPage() {
  const { id } = useParams();
  const isEdit = Boolean(id);
  const navigate = useNavigate();
  const [form, setForm] = useState(blank);
  const [assignees, setAssignees] = useState([]);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.get("/users/assignees").then((r) => setAssignees(r.data)).catch(() => {});
    if (isEdit) {
      api
        .get(`/devices/${id}`)
        .then((r) => {
          const d = r.data;
          setForm({
            device_name: d.device_name,
            device_nickname: d.device_nickname,
            device_type: d.device_type,
            os_type: d.os_type,
            os_version: d.os_version,
            audit_status: d.audit_status || "pending_audit",
            resident_location: d.resident_location || "",
            division: d.division || "",
            issued_to: d.issued_to || "",
            project_manager: d.project_manager || "",
            project_name: d.project_name || "",
            date_of_return: d.date_of_return || "",
            is_latest_model: d.is_latest_model || false,
            is_cellular: d.is_cellular,
            imei_number: d.imei_number || "",
            serial_number: d.serial_number,
            mac_address: d.mac_address,
            company: d.company,
            assigned_user_id: d.assigned_user_id || "",
            status: d.status,
            purchase_date: d.purchase_date || "",
          });
        })
        .catch((e) => setError(e.response?.data?.detail || "Failed to load device"));
    }
  }, [id, isEdit]);

  const onChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm((f) => ({ ...f, [name]: type === "checkbox" ? checked : value }));
  };

  const validateClient = () => {
    if (form.is_cellular && !/^\d{15}$/.test(form.imei_number)) {
      return "IMEI is required and must be 15 digits for cellular devices";
    }
    if (!form.is_cellular && form.imei_number) {
      return "Clear IMEI for non-cellular devices";
    }
    if (!/^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$/.test(form.mac_address)) {
      return "MAC must match XX:XX:XX:XX:XX:XX";
    }
    return "";
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    const clientError = validateClient();
    if (clientError) {
      setError(clientError);
      return;
    }
    setSaving(true);
    setError("");
    const payload = {
      ...form,
      imei_number: form.is_cellular ? form.imei_number : null,
      assigned_user_id: form.assigned_user_id || null,
      audit_status: form.audit_status || null,
      resident_location: form.resident_location || null,
      division: form.division || null,
      issued_to: form.issued_to || null,
      project_manager: form.project_manager || null,
      project_name: form.project_name || null,
      date_of_return: form.date_of_return || null,
      purchase_date: form.purchase_date || null,
    };

    try {
      if (isEdit) {
        const body = { ...payload };
        if (!form.assigned_user_id) body.clear_assigned_user = true;
        if (!form.is_cellular) body.clear_imei = true;
        if (!form.purchase_date) body.clear_purchase_date = true;
        if (!form.date_of_return) body.clear_date_of_return = true;
        await api.patch(`/devices/${id}`, body);
        navigate(`/devices/${id}`);
      } else {
        const { data } = await api.post("/devices", payload);
        navigate(`/devices/${data.id}`);
      }
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === "string" ? detail : JSON.stringify(detail) || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="page">
      <div className="page-head">
        <div>
          <h1>{isEdit ? "Edit device" : "Add device"}</h1>
          <p className="lede">Capture identifiers and assignment in one place.</p>
        </div>
      </div>

      <form className="form-grid" onSubmit={onSubmit}>
        <label>
          Device name
          <input name="device_name" value={form.device_name} onChange={onChange} required />
        </label>
        <label>
          Name / AKA
          <input name="device_nickname" value={form.device_nickname} onChange={onChange} required />
        </label>
        <label>
          Type
          <select name="device_type" value={form.device_type} onChange={onChange}>
            {DEVICE_TYPES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          OS
          <select name="os_type" value={form.os_type} onChange={onChange}>
            {OS_TYPES.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          OS version
          <input name="os_version" value={form.os_version} onChange={onChange} required />
        </label>
        <label>
          Audit status
          <select name="audit_status" value={form.audit_status} onChange={onChange}>
            {AUDIT_STATUSES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
        <label className="checkbox">
          <input name="is_cellular" type="checkbox" checked={form.is_cellular} onChange={onChange} />
          Cellular capable (IMEI required)
        </label>
        {form.is_cellular && (
          <label>
            IMEI (15 digits)
            <input name="imei_number" value={form.imei_number} onChange={onChange} required />
          </label>
        )}
        <label>
          Company Serial
          <input name="serial_number" value={form.serial_number} onChange={onChange} required />
        </label>
        <label>
          MAC address
          <input
            name="mac_address"
            placeholder="AA:BB:CC:DD:EE:FF"
            value={form.mac_address}
            onChange={onChange}
            required
          />
        </label>
        <label>
          Company
          <input name="company" value={form.company} onChange={onChange} required />
        </label>
        <label>
          Issued to (Engineer Name)
          <div style={{display: 'flex', gap: '8px'}}>
            <input name="issued_to" value={form.issued_to} onChange={onChange} />
            <input name="issued_to_email" value={form.issued_to_email} onChange={onChange} placeholder="email@example.com" />
          </div>
        </label>
        <label>
          Resident location
          <input name="resident_location" value={form.resident_location} onChange={onChange} />
        </label>
        <label>
          Division
          <input name="division" value={form.division} onChange={onChange} />
        </label>
        <label>
          Project manager
          <input name="project_manager" value={form.project_manager} onChange={onChange} />
        </label>
        <label>
          Project name
          <input name="project_name" value={form.project_name} onChange={onChange} />
        </label>
        <label className="checkbox">
          <input
            type="checkbox"
            name="is_latest_model"
            checked={form.is_latest_model}
            onChange={onChange}
          />
          Mark as Latest Model
        </label>
        <label>
          Date of return
          <input type="date" name="date_of_return" value={form.date_of_return} onChange={onChange} />
        </label>
        <label>
          Assigned user
          <select name="assigned_user_id" value={form.assigned_user_id} onChange={onChange}>
            <option value="">Unassigned</option>
            {assignees.map((u) => (
              <option key={u.id} value={u.id}>
                {u.full_name} ({u.email})
              </option>
            ))}
          </select>
        </label>
        <label>
          Status
          <select name="status" value={form.status} onChange={onChange}>
            {STATUSES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Purchase date
          <input type="date" name="purchase_date" value={form.purchase_date} onChange={onChange} />
        </label>

        {error && <p className="error full">{error}</p>}
        <div className="actions full">
          <button className="btn primary" type="submit" disabled={saving}>
            {saving ? "Saving…" : "Save device"}
          </button>
          <button className="btn ghost" type="button" onClick={() => navigate(-1)}>
            Cancel
          </button>
        </div>
      </form>
    </section>
  );
}
