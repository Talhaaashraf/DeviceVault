import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import api from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { DEVICE_TYPES, OS_TYPES, labelOf } from "../constants";

export default function ManagementPage() {
  const { user, canManage, isAdmin } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const activeTab = searchParams.get("tab") || "requests";

  const setTab = (tab) => {
    setSearchParams({ tab });
  };

  // Shared state
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState({ error: "", success: "" });

  // 1. Requests state
  const [requests, setRequests] = useState([]);
  const [requestFilter, setRequestFilter] = useState("all");
  const [showRequestModal, setShowRequestModal] = useState(false);
  const [showFulfillModal, setShowFulfillModal] = useState(null); // request to fulfill
  const [newRequest, setNewRequest] = useState({
    device_type: "phone",
    os_preference: "ios",
    project_name: "",
    division: "",
    reason: "",
    duration_days: 14,
    date_needed: "",
  });
  const [fulfillForm, setFulfillForm] = useState({
    device_id: "",
    date_of_return: "",
    notes: "",
  });

  // 2. Maintenance state
  const [tickets, setTickets] = useState([]);
  const [maintenanceFilter, setMaintenanceFilter] = useState("active");
  const [showTicketModal, setShowTicketModal] = useState(false);
  const [updateTicketTarget, setUpdateTicketTarget] = useState(null);
  const [newTicket, setNewTicket] = useState({
    device_id: "",
    issue_title: "",
    issue_description: "",
    priority: "medium",
    vendor_name: "",
    estimated_cost: 0,
    sent_date: new Date().toISOString().slice(0, 10),
  });
  const [ticketUpdateForm, setTicketUpdateForm] = useState({
    repair_status: "completed",
    actual_cost: 0,
    technician_notes: "",
    completed_date: new Date().toISOString().slice(0, 10),
  });

  // 3. Returns state
  const [returnsData, setReturnsData] = useState({
    overdue_count: 0,
    due_soon_count: 0,
    total_assigned: 0,
    overdue_devices: [],
    due_soon_devices: [],
  });
  const [extendTarget, setExtendTarget] = useState(null);
  const [extendForm, setExtendForm] = useState({ new_return_date: "", extension_reason: "" });
  const [returnTarget, setReturnTarget] = useState(null);
  const [returnForm, setReturnForm] = useState({ condition: "Good", return_notes: "" });
  const [clearanceSlip, setClearanceSlip] = useState(null);

  // 4. Audits state
  const [auditCycles, setAuditCycles] = useState([]);
  const [selectedCycle, setSelectedCycle] = useState("2026-Q3");
  const [auditLogs, setAuditLogs] = useState([]);
  const [showAuditModal, setShowAuditModal] = useState(false);
  const [auditForm, setAuditForm] = useState({
    device_id: "",
    audit_cycle: "2026-Q3",
    physical_status: "confirmed",
    verified_location: "",
    notes: "",
  });

  // 5. Allocations state
  const [allocations, setAllocations] = useState(null);

  // Clear messages
  const notify = (successMsg = "", errorMsg = "") => {
    setMsg({ success: successMsg, error: errorMsg });
    if (successMsg) setTimeout(() => setMsg({ error: "", success: "" }), 5000);
  };

  // Load active tab data
  const loadData = async () => {
    setLoading(true);
    try {
      // Always get device list for select dropdowns
      const devRes = await api.get("/devices");
      setDevices(devRes.data);

      if (activeTab === "requests") {
        const reqRes = await api.get("/management/requests");
        setRequests(reqRes.data);
      } else if (activeTab === "maintenance") {
        const tRes = await api.get("/management/maintenance");
        setTickets(tRes.data);
      } else if (activeTab === "returns") {
        const rRes = await api.get("/management/returns");
        setReturnsData(rRes.data);
      } else if (activeTab === "audits") {
        const [cRes, lRes] = await Promise.all([
          api.get("/management/audits/cycles"),
          api.get(`/management/audits?cycle=${selectedCycle}`),
        ]);
        setAuditCycles(cRes.data);
        if (cRes.data.length > 0 && !selectedCycle) {
          setSelectedCycle(cRes.data[0].audit_cycle);
        }
        setAuditLogs(lRes.data);
      } else if (activeTab === "allocations") {
        const aRes = await api.get("/management/allocations");
        setAllocations(aRes.data);
      }
    } catch (e) {
      notify("", e.response?.data?.detail || "Failed to load management data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [activeTab, selectedCycle]);

  // Request actions
  const handleCreateRequest = async (e) => {
    e.preventDefault();
    try {
      await api.post("/management/requests", newRequest);
      setShowRequestModal(false);
      notify("Device request submitted successfully!");
      loadData();
    } catch (e) {
      notify("", e.response?.data?.detail || "Failed to create request");
    }
  };

  const handleReviewRequest = async (requestId, status) => {
    const notes = window.prompt(`Enter manager note for ${status}:`, "") ?? "";
    try {
      await api.post(`/management/requests/${requestId}/review`, {
        status,
        manager_notes: notes,
      });
      notify(`Request marked as ${status}`);
      loadData();
    } catch (e) {
      notify("", e.response?.data?.detail || "Failed to review request");
    }
  };

  const handleFulfillRequest = async (e) => {
    e.preventDefault();
    if (!fulfillForm.device_id) return notify("", "Please select a device to allocate");
    try {
      await api.post(`/management/requests/${showFulfillModal.id}/fulfill`, fulfillForm);
      setShowFulfillModal(null);
      notify("Device successfully allocated to requester!");
      loadData();
    } catch (e) {
      notify("", e.response?.data?.detail || "Failed to allocate device");
    }
  };

  // Maintenance actions
  const handleCreateTicket = async (e) => {
    e.preventDefault();
    if (!newTicket.device_id) return notify("", "Please select a device");
    try {
      await api.post("/management/maintenance", newTicket);
      setShowTicketModal(false);
      notify("Maintenance ticket logged! Device status set to In Repair.");
      loadData();
    } catch (e) {
      notify("", e.response?.data?.detail || "Failed to log maintenance ticket");
    }
  };

  const handleUpdateTicket = async (e) => {
    e.preventDefault();
    try {
      await api.patch(`/management/maintenance/${updateTicketTarget.id}`, ticketUpdateForm);
      setUpdateTicketTarget(null);
      notify("Ticket updated successfully!");
      loadData();
    } catch (e) {
      notify("", e.response?.data?.detail || "Failed to update maintenance ticket");
    }
  };

  // Returns actions
  const handleExtendReturn = async (e) => {
    e.preventDefault();
    try {
      await api.post(`/management/returns/${extendTarget.device_id}/extend`, extendForm);
      setExtendTarget(null);
      notify("Return date extended successfully!");
      loadData();
    } catch (e) {
      notify("", e.response?.data?.detail || "Failed to extend return date");
    }
  };

  const handleProcessReturn = async (e) => {
    e.preventDefault();
    try {
      await api.post(`/management/returns/${returnTarget.device_id}/return`, returnForm);
      setClearanceSlip({
        device: returnTarget,
        condition: returnForm.condition,
        notes: returnForm.return_notes,
        returned_at: new Date().toLocaleDateString(),
        processed_by: user.full_name,
      });
      setReturnTarget(null);
      notify("Device returned! Placed back in available inventory pool.");
      loadData();
    } catch (e) {
      notify("", e.response?.data?.detail || "Failed to process return");
    }
  };

  // Audit actions
  const handleRecordAudit = async (e) => {
    e.preventDefault();
    if (!auditForm.device_id) return notify("", "Please select a device to verify");
    try {
      await api.post("/management/audits", {
        ...auditForm,
        audit_cycle: selectedCycle || auditForm.audit_cycle,
      });
      setShowAuditModal(false);
      notify("Physical verification recorded successfully!");
      loadData();
    } catch (e) {
      notify("", e.response?.data?.detail || "Failed to record audit verification");
    }
  };

  // Quick stats calculations
  const pendingRequestsCount = requests.filter((r) => r.status === "pending").length;
  const activeTicketsCount = tickets.filter((t) => t.repair_status !== "completed").length;
  const overdueCount = returnsData.overdue_count;

  // Filtered requests
  const filteredRequests = requests.filter((r) => {
    if (requestFilter === "all") return true;
    return r.status === requestFilter;
  });

  // Filtered maintenance tickets
  const filteredTickets = tickets.filter((t) => {
    if (maintenanceFilter === "active") return t.repair_status !== "completed";
    if (maintenanceFilter === "completed") return t.repair_status === "completed";
    return true;
  });

  const currentCycleSummary =
    auditCycles.find((c) => c.audit_cycle === selectedCycle) || auditCycles[0];

  return (
    <section className="page">
      <div className="page-head">
        <div>
          <p className="eyebrow">Enterprise Operations</p>
          <h1>Operations Management Hub</h1>
          <p className="lede">
            Unified workflows for device requests, repair tracking, returns & overdue items, physical
            audits, and departmental allocation analytics.
          </p>
        </div>
      </div>

      {msg.error && <div className="alert error">{msg.error}</div>}
      {msg.success && <div className="alert success">{msg.success}</div>}

      {/* Modern Navigation Tabs */}
      <div className="mgmt-tabs">
        <button
          className={`mgmt-tab-btn ${activeTab === "requests" ? "active" : ""}`}
          onClick={() => setTab("requests")}
          type="button"
        >
          <span>📋 Device Requests</span>
          {pendingRequestsCount > 0 && <span className="tab-badge">{pendingRequestsCount}</span>}
        </button>
        <button
          className={`mgmt-tab-btn ${activeTab === "maintenance" ? "active" : ""}`}
          onClick={() => setTab("maintenance")}
          type="button"
        >
          <span>🔧 Maintenance & Repairs</span>
          {activeTicketsCount > 0 && <span className="tab-badge warn">{activeTicketsCount}</span>}
        </button>
        <button
          className={`mgmt-tab-btn ${activeTab === "returns" ? "active" : ""}`}
          onClick={() => setTab("returns")}
          type="button"
        >
          <span>⏰ Returns & Overdue</span>
          {overdueCount > 0 && <span className="tab-badge danger">{overdueCount}</span>}
        </button>
        <button
          className={`mgmt-tab-btn ${activeTab === "audits" ? "active" : ""}`}
          onClick={() => setTab("audits")}
          type="button"
        >
          <span>🛡️ Audit & Verification</span>
        </button>
        <button
          className={`mgmt-tab-btn ${activeTab === "allocations" ? "active" : ""}`}
          onClick={() => setTab("allocations")}
          type="button"
        >
          <span>📊 Dept & Project Allocation</span>
        </button>
      </div>

      {/* ========================================================= */}
      {/* TAB 1: DEVICE REQUESTS & APPROVALS                        */}
      {/* ========================================================= */}
      {activeTab === "requests" && (
        <div className="tab-content">
          <div className="tab-header">
            <div>
              <h2>Device Requests & Approvals</h2>
              <p className="muted">
                Submit device allocation requests. Managers can review, approve, or allocate devices with one click.
              </p>
            </div>
            <div className="actions">
              <button
                className="btn primary"
                type="button"
                onClick={() => setShowRequestModal(true)}
              >
                + New Device Request
              </button>
            </div>
          </div>

          <div className="filter-chips">
            {["all", "pending", "approved", "fulfilled", "rejected"].map((f) => (
              <button
                key={f}
                className={`chip ${requestFilter === f ? "active" : ""}`}
                onClick={() => setRequestFilter(f)}
                type="button"
              >
                {f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Requested Device</th>
                  <th>Requester</th>
                  <th>Project / Division</th>
                  <th>Duration / Date Needed</th>
                  <th>Status</th>
                  <th>Manager Notes</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredRequests.length === 0 ? (
                  <tr>
                    <td colSpan="7" style={{ textAlign: "center", padding: "2rem" }}>
                      No device requests found for this filter.
                    </td>
                  </tr>
                ) : (
                  filteredRequests.map((r) => (
                    <tr key={r.id}>
                      <td>
                        <strong>{labelOf(DEVICE_TYPES, r.device_type)}</strong>
                        <div className="small-muted">
                          Pref: {r.os_preference ? labelOf(OS_TYPES, r.os_preference) : "Any"}
                        </div>
                      </td>
                      <td>
                        <strong>{r.user?.full_name || "Unknown"}</strong>
                        <div className="small-muted">{r.user?.email}</div>
                      </td>
                      <td>
                        <strong>{r.project_name}</strong>
                        <div className="small-muted">{r.division || "—"}</div>
                      </td>
                      <td>
                        <strong>{r.duration_days ? `${r.duration_days} days` : "Permanent"}</strong>
                        <div className="small-muted">
                          Needed: {r.date_needed ? r.date_needed : "Immediately"}
                        </div>
                      </td>
                      <td>
                        <span className={`pill req-${r.status}`}>
                          {r.status.toUpperCase()}
                        </span>
                      </td>
                      <td>
                        <span>{r.manager_notes || "—"}</span>
                        {r.allocated_device && (
                          <div className="small-muted">
                            Allocated:{" "}
                            <Link to={`/devices/${r.allocated_device.id}`}>
                              {r.allocated_device.device_name}
                            </Link>
                          </div>
                        )}
                      </td>
                      <td>
                        <div className="actions">
                          {canManage && r.status === "pending" && (
                            <>
                              <button
                                className="btn sm primary"
                                type="button"
                                onClick={() => handleReviewRequest(r.id, "approved")}
                              >
                                Approve
                              </button>
                              <button
                                className="btn sm ghost"
                                type="button"
                                onClick={() => handleReviewRequest(r.id, "rejected")}
                              >
                                Reject
                              </button>
                            </>
                          )}
                          {canManage && r.status === "approved" && (
                            <button
                              className="btn sm accent"
                              type="button"
                              onClick={() => {
                                setShowFulfillModal(r);
                                setFulfillForm({
                                  device_id: "",
                                  date_of_return: "",
                                  notes: `Fulfilled for project ${r.project_name}`,
                                });
                              }}
                            >
                              Allocate Device
                            </button>
                          )}
                          {r.status === "fulfilled" && (
                            <span className="small-muted">Completed</span>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* TAB 2: MAINTENANCE & REPAIRS                             */}
      {/* ========================================================= */}
      {activeTab === "maintenance" && (
        <div className="tab-content">
          <div className="tab-header">
            <div>
              <h2>Maintenance & Repair Tracking</h2>
              <p className="muted">
                Log repair tickets, track vendor costs and progress, and automatically restore repaired devices back to active inventory.
              </p>
            </div>
            <div className="actions">
              {canManage && (
                <button
                  className="btn primary"
                  type="button"
                  onClick={() => setShowTicketModal(true)}
                >
                  + Log Repair Ticket
                </button>
              )}
            </div>
          </div>

          <div className="stat-grid-3">
            <div className="stat-card">
              <span className="stat-label">Active Repairs</span>
              <strong className="stat-val">{activeTicketsCount}</strong>
              <span className="stat-sub">Devices currently being serviced</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">Total Repair Expense</span>
              <strong className="stat-val">
                ${tickets.reduce((sum, t) => sum + (t.actual_cost || t.estimated_cost || 0), 0).toFixed(2)}
              </strong>
              <span className="stat-sub">Across all tickets</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">Completed Repairs</span>
              <strong className="stat-val">
                {tickets.filter((t) => t.repair_status === "completed").length}
              </strong>
              <span className="stat-sub">Returned to available pool</span>
            </div>
          </div>

          <div className="filter-chips">
            {["active", "completed", "all"].map((f) => (
              <button
                key={f}
                className={`chip ${maintenanceFilter === f ? "active" : ""}`}
                onClick={() => setMaintenanceFilter(f)}
                type="button"
              >
                {f === "active" ? "In Service" : f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Device</th>
                  <th>Issue & Priority</th>
                  <th>Vendor</th>
                  <th>Cost (Est / Act)</th>
                  <th>Dates</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredTickets.length === 0 ? (
                  <tr>
                    <td colSpan="7" style={{ textAlign: "center", padding: "2rem" }}>
                      No maintenance tickets in this category.
                    </td>
                  </tr>
                ) : (
                  filteredTickets.map((t) => (
                    <tr key={t.id}>
                      <td>
                        <strong>
                          <Link to={`/devices/${t.device_id}`}>
                            {t.device?.device_name || "Device"}
                          </Link>
                        </strong>
                        <div className="small-muted">
                          SN: {t.device?.serial_number} · {t.device?.device_nickname}
                        </div>
                      </td>
                      <td>
                        <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
                          <span className={`priority-dot p-${t.priority}`} />
                          <strong>{t.issue_title}</strong>
                        </div>
                        {t.issue_description && (
                          <div className="small-muted">{t.issue_description}</div>
                        )}
                      </td>
                      <td>
                        <strong>{t.vendor_name || "Internal / TBD"}</strong>
                      </td>
                      <td>
                        <div>Est: ${t.estimated_cost?.toFixed(2) || "0.00"}</div>
                        {t.actual_cost ? (
                          <strong className="small-muted">
                            Act: ${t.actual_cost?.toFixed(2)}
                          </strong>
                        ) : null}
                      </td>
                      <td>
                        <div className="small-muted">Sent: {t.sent_date || "—"}</div>
                        {t.completed_date && (
                          <div className="small-muted">Done: {t.completed_date}</div>
                        )}
                      </td>
                      <td>
                        <span className={`pill status-${t.repair_status}`}>
                          {t.repair_status.replace("_", " ").toUpperCase()}
                        </span>
                      </td>
                      <td>
                        {canManage && t.repair_status !== "completed" && (
                          <button
                            className="btn sm secondary"
                            type="button"
                            onClick={() => {
                              setUpdateTicketTarget(t);
                              setTicketUpdateForm({
                                repair_status: "completed",
                                actual_cost: t.actual_cost || t.estimated_cost || 0,
                                technician_notes: t.technician_notes || "",
                                completed_date: new Date().toISOString().slice(0, 10),
                              });
                            }}
                          >
                            Update / Resolve
                          </button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* TAB 3: RETURNS & OVERDUE MANAGEMENT                       */}
      {/* ========================================================= */}
      {activeTab === "returns" && (
        <div className="tab-content">
          <div className="tab-header">
            <div>
              <h2>Device Returns & Overdue Hub</h2>
              <p className="muted">
                Monitor devices past their return deadline, extend return dates, process check-ins, and print clearance receipts.
              </p>
            </div>
          </div>

          <div className="stat-grid-3">
            <div className="stat-card danger-card">
              <span className="stat-label">🚨 Overdue Devices</span>
              <strong className="stat-val">{returnsData.overdue_count}</strong>
              <span className="stat-sub">Return deadline has passed</span>
            </div>
            <div className="stat-card warn-card">
              <span className="stat-label">⏳ Due Next 7 Days</span>
              <strong className="stat-val">{returnsData.due_soon_count}</strong>
              <span className="stat-sub">Upcoming scheduled returns</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">📱 Total Active Assignments</span>
              <strong className="stat-val">{returnsData.total_assigned}</strong>
              <span className="stat-sub">In field or employee possession</span>
            </div>
          </div>

          <div className="section-block">
            <h3 style={{ color: "var(--danger)", display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <span>⚠️ Overdue Devices ({returnsData.overdue_devices.length})</span>
            </h3>

            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Device</th>
                    <th>Current Assignee</th>
                    <th>Project / Division</th>
                    <th>Scheduled Return</th>
                    <th>Days Overdue</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {returnsData.overdue_devices.length === 0 ? (
                    <tr>
                      <td colSpan="6" style={{ textAlign: "center", padding: "1.5rem", color: "var(--accent)" }}>
                        🎉 Great job! No devices are currently overdue.
                      </td>
                    </tr>
                  ) : (
                    returnsData.overdue_devices.map((d) => (
                      <tr key={d.device_id} className="row-alert">
                        <td>
                          <strong>
                            <Link to={`/devices/${d.device_id}`}>{d.device_name}</Link>
                          </strong>
                          <div className="small-muted">SN: {d.serial_number}</div>
                        </td>
                        <td>
                          <strong>{d.assigned_user_name || d.issued_to || "Unknown"}</strong>
                          <div className="small-muted">{d.issued_to_email}</div>
                        </td>
                        <td>
                          <strong>{d.project_name || "—"}</strong>
                          <div className="small-muted">{d.division || "—"}</div>
                        </td>
                        <td>
                          <strong>{d.date_of_return}</strong>
                        </td>
                        <td>
                          <span className="pill badge-danger">
                            {d.days_overdue} days late
                          </span>
                        </td>
                        <td>
                          <div className="actions">
                            {canManage && (
                              <>
                                <button
                                  className="btn sm secondary"
                                  type="button"
                                  onClick={() => {
                                    setExtendTarget(d);
                                    setExtendForm({
                                      new_return_date: new Date(Date.now() + 7 * 86400000)
                                        .toISOString()
                                        .slice(0, 10),
                                      extension_reason: "Project deadline extended",
                                    });
                                  }}
                                >
                                  Extend Date
                                </button>
                                <button
                                  className="btn sm primary"
                                  type="button"
                                  onClick={() => {
                                    setReturnTarget(d);
                                    setReturnForm({ condition: "Good", return_notes: "" });
                                  }}
                                >
                                  Process Return
                                </button>
                              </>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <div className="section-block" style={{ marginTop: "2rem" }}>
            <h3>Upcoming Returns (Next 7 Days)</h3>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Device</th>
                    <th>Assignee</th>
                    <th>Project</th>
                    <th>Due Date</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {returnsData.due_soon_devices.length === 0 ? (
                    <tr>
                      <td colSpan="5" style={{ textAlign: "center", padding: "1.5rem" }}>
                        No devices scheduled for return in the next 7 days.
                      </td>
                    </tr>
                  ) : (
                    returnsData.due_soon_devices.map((d) => (
                      <tr key={d.device_id}>
                        <td>
                          <strong>
                            <Link to={`/devices/${d.device_id}`}>{d.device_name}</Link>
                          </strong>
                          <div className="small-muted">SN: {d.serial_number}</div>
                        </td>
                        <td>{d.assigned_user_name || d.issued_to}</td>
                        <td>{d.project_name || "—"}</td>
                        <td>
                          <span className="pill badge-warn">{d.date_of_return}</span>
                        </td>
                        <td>
                          {canManage && (
                            <div className="actions">
                              <button
                                className="btn sm ghost"
                                type="button"
                                onClick={() => {
                                  setExtendTarget(d);
                                  setExtendForm({
                                    new_return_date: new Date(Date.now() + 14 * 86400000)
                                      .toISOString()
                                      .slice(0, 10),
                                    extension_reason: "",
                                  });
                                }}
                              >
                                Extend
                              </button>
                              <button
                                className="btn sm primary"
                                type="button"
                                onClick={() => {
                                  setReturnTarget(d);
                                  setReturnForm({ condition: "Good", return_notes: "" });
                                }}
                              >
                                Receive Return
                              </button>
                            </div>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* TAB 4: AUDIT & PHYSICAL VERIFICATION                      */}
      {/* ========================================================= */}
      {activeTab === "audits" && (
        <div className="tab-content">
          <div className="tab-header">
            <div>
              <h2>Physical Audit & Verification</h2>
              <p className="muted">
                Execute quarterly physical inventory audits, record barcode/physical verifications, and detect missing or damaged hardware.
              </p>
            </div>
            <div className="actions">
              {canManage && (
                <button
                  className="btn primary"
                  type="button"
                  onClick={() => setShowAuditModal(true)}
                >
                  + Record Device Verification
                </button>
              )}
            </div>
          </div>

          <div className="audit-cycle-bar">
            <div className="cycle-selector">
              <label><strong>Audit Cycle:</strong></label>
              <select
                value={selectedCycle}
                onChange={(e) => setSelectedCycle(e.target.value)}
              >
                {auditCycles.map((c) => (
                  <option key={c.audit_cycle} value={c.audit_cycle}>
                    {c.audit_cycle} ({c.completion_percentage}% verified)
                  </option>
                ))}
              </select>
            </div>

            {currentCycleSummary && (
              <div className="audit-meter-card">
                <div className="audit-meter-header">
                  <span>Cycle Progress: <strong>{currentCycleSummary.audited_devices} / {currentCycleSummary.total_devices} devices verified</strong></span>
                  <strong>{currentCycleSummary.completion_percentage}%</strong>
                </div>
                <div className="progress-track">
                  <div
                    className="progress-fill"
                    style={{ width: `${currentCycleSummary.completion_percentage}%` }}
                  />
                </div>
                <div className="audit-chips-row">
                  <span className="pill badge-success">✓ {currentCycleSummary.confirmed_count} Confirmed</span>
                  {currentCycleSummary.missing_count > 0 && (
                    <span className="pill badge-danger">✗ {currentCycleSummary.missing_count} Missing</span>
                  )}
                  {currentCycleSummary.damaged_count > 0 && (
                    <span className="pill badge-warn">⚠️ {currentCycleSummary.damaged_count} Damaged</span>
                  )}
                  {currentCycleSummary.disputed_count > 0 && (
                    <span className="pill badge-dispute">❓ {currentCycleSummary.disputed_count} Disputed</span>
                  )}
                </div>
              </div>
            )}
          </div>

          <div className="table-wrap" style={{ marginTop: "1.5rem" }}>
            <table>
              <thead>
                <tr>
                  <th>Device Name</th>
                  <th>Serial Number</th>
                  <th>Physical Verification</th>
                  <th>Verified Location</th>
                  <th>Auditor</th>
                  <th>Audit Date</th>
                  <th>Notes</th>
                </tr>
              </thead>
              <tbody>
                {auditLogs.length === 0 ? (
                  <tr>
                    <td colSpan="7" style={{ textAlign: "center", padding: "2rem" }}>
                      No audit verification records found for cycle {selectedCycle}.
                    </td>
                  </tr>
                ) : (
                  auditLogs.map((log) => (
                    <tr key={log.id}>
                      <td>
                        <strong>
                          <Link to={`/devices/${log.device_id}`}>
                            {log.device?.device_name || "Device"}
                          </Link>
                        </strong>
                      </td>
                      <td>
                        <code>{log.device?.serial_number}</code>
                      </td>
                      <td>
                        <span className={`pill audit-${log.physical_status}`}>
                          {log.physical_status.toUpperCase()}
                        </span>
                      </td>
                      <td>{log.verified_location || "—"}</td>
                      <td>{log.auditor?.full_name || "Auditor"}</td>
                      <td>{new Date(log.created_at).toLocaleString()}</td>
                      <td>{log.notes || "—"}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* TAB 5: DEPARTMENT & PROJECT ASSET ALLOCATION              */}
      {/* ========================================================= */}
      {activeTab === "allocations" && allocations && (
        <div className="tab-content">
          <div className="tab-header">
            <div>
              <h2>Department & Project Asset Allocation</h2>
              <p className="muted">
                Analyze device allocation, asset utilization across teams, and identify bottlenecks and unassigned hardware.
              </p>
            </div>
          </div>

          <div className="stat-grid-4">
            <div className="stat-card">
              <span className="stat-label">Total Fleet</span>
              <strong className="stat-val">{allocations.total_devices}</strong>
              <span className="stat-sub">Hardware devices in system</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">Assigned Assets</span>
              <strong className="stat-val">{allocations.assigned_devices}</strong>
              <span className="stat-sub">In active deployment</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">Fleet Utilization</span>
              <strong className="stat-val" style={{ color: "var(--accent)" }}>
                {allocations.utilization_rate}%
              </strong>
              <span className="stat-sub">Deployed ratio</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">Available / Bench</span>
              <strong className="stat-val">{allocations.unassigned_devices}</strong>
              <span className="stat-sub">Ready for allocation</span>
            </div>
          </div>

          <div className="allocation-grid" style={{ marginTop: "2rem" }}>
            <div className="panel">
              <h3>Allocation by Division / Department</h3>
              <ul className="allocation-list">
                {allocations.by_division.map((item) => (
                  <li key={item.name}>
                    <div className="alloc-header">
                      <strong>{item.name}</strong>
                      <span>
                        <strong>{item.device_count} devices</strong> ({item.percentage}%)
                        {item.overdue_count > 0 && (
                          <span className="badge-danger-sm"> {item.overdue_count} overdue</span>
                        )}
                      </span>
                    </div>
                    <div className="progress-track sm">
                      <div className="progress-fill" style={{ width: `${item.percentage}%` }} />
                    </div>
                  </li>
                ))}
              </ul>
            </div>

            <div className="panel">
              <h3>Allocation by Project</h3>
              <ul className="allocation-list">
                {allocations.by_project.map((item) => (
                  <li key={item.name}>
                    <div className="alloc-header">
                      <strong>{item.name}</strong>
                      <span>
                        <strong>{item.device_count} devices</strong> ({item.percentage}%)
                        {item.overdue_count > 0 && (
                          <span className="badge-danger-sm"> {item.overdue_count} overdue</span>
                        )}
                      </span>
                    </div>
                    <div className="progress-track sm">
                      <div
                        className="progress-fill"
                        style={{ width: `${item.percentage}%`, background: "var(--accent-2)" }}
                      />
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="panel" style={{ marginTop: "1.5rem" }}>
            <h3>Hardware Distribution by Resident Location</h3>
            <div className="location-cards-row">
              {allocations.by_location.map((item) => (
                <div key={item.name} className="loc-card">
                  <strong>📍 {item.name}</strong>
                  <div className="stat-val" style={{ fontSize: "1.8rem" }}>
                    {item.device_count}
                  </div>
                  <span className="small-muted">{item.percentage}% of inventory</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* MODALS                                                    */}
      {/* ========================================================= */}

      {/* Modal: New Device Request */}
      {showRequestModal && (
        <div className="modal-backdrop" onClick={() => setShowRequestModal(false)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <h3>Submit New Device Request</h3>
            <form onSubmit={handleCreateRequest} className="stack">
              <label>
                Device Type *
                <select
                  value={newRequest.device_type}
                  onChange={(e) => setNewRequest({ ...newRequest, device_type: e.target.value })}
                  required
                >
                  {DEVICE_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </select>
              </label>
              <label>
                OS Preference
                <select
                  value={newRequest.os_preference}
                  onChange={(e) => setNewRequest({ ...newRequest, os_preference: e.target.value })}
                >
                  <option value="">Any / No preference</option>
                  {OS_TYPES.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </label>
              <label>
                Project Name *
                <input
                  type="text"
                  value={newRequest.project_name}
                  onChange={(e) => setNewRequest({ ...newRequest, project_name: e.target.value })}
                  placeholder="e.g. Mobile Banking 2.0"
                  required
                />
              </label>
              <label>
                Department / Division
                <input
                  type="text"
                  value={newRequest.division}
                  onChange={(e) => setNewRequest({ ...newRequest, division: e.target.value })}
                  placeholder="e.g. QA Automation"
                />
              </label>
              <div className="grid-2">
                <label>
                  Duration (Days)
                  <input
                    type="number"
                    min="1"
                    value={newRequest.duration_days}
                    onChange={(e) => setNewRequest({ ...newRequest, duration_days: parseInt(e.target.value) || 14 })}
                  />
                </label>
                <label>
                  Date Needed
                  <input
                    type="date"
                    value={newRequest.date_needed}
                    onChange={(e) => setNewRequest({ ...newRequest, date_needed: e.target.value })}
                  />
                </label>
              </div>
              <label>
                Business Justification / Reason *
                <textarea
                  rows="3"
                  value={newRequest.reason}
                  onChange={(e) => setNewRequest({ ...newRequest, reason: e.target.value })}
                  placeholder="State the testing, development, or business purpose for this device..."
                  required
                />
              </label>
              <div className="actions" style={{ marginTop: "1rem", justifyContent: "flex-end" }}>
                <button className="btn ghost" type="button" onClick={() => setShowRequestModal(false)}>
                  Cancel
                </button>
                <button className="btn primary" type="submit">
                  Submit Request
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Fulfill Request & Allocate Device */}
      {showFulfillModal && (
        <div className="modal-backdrop" onClick={() => setShowFulfillModal(null)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <h3>Allocate Device for Request</h3>
            <p className="muted">
              Requester: <strong>{showFulfillModal.user?.full_name}</strong> · Project: <strong>{showFulfillModal.project_name}</strong>
            </p>
            <form onSubmit={handleFulfillRequest} className="stack">
              <label>
                Select Active Device to Assign *
                <select
                  value={fulfillForm.device_id}
                  onChange={(e) => setFulfillForm({ ...fulfillForm, device_id: e.target.value })}
                  required
                >
                  <option value="">-- Choose an available device --</option>
                  {devices
                    .filter((d) => d.status === "active" && !d.assigned_user_id && !d.issued_to)
                    .map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.device_name} ({d.serial_number})
                      </option>
                    ))}
                </select>
              </label>
              <label>
                Expected Date of Return
                <input
                  type="date"
                  value={fulfillForm.date_of_return}
                  onChange={(e) => setFulfillForm({ ...fulfillForm, date_of_return: e.target.value })}
                />
              </label>
              <label>
                Allocation Notes
                <input
                  type="text"
                  value={fulfillForm.notes}
                  onChange={(e) => setFulfillForm({ ...fulfillForm, notes: e.target.value })}
                  placeholder="e.g. Handed over with charger and protective case"
                />
              </label>
              <div className="actions" style={{ marginTop: "1rem", justifyContent: "flex-end" }}>
                <button className="btn ghost" type="button" onClick={() => setShowFulfillModal(null)}>
                  Cancel
                </button>
                <button className="btn primary" type="submit">
                  Assign & Fulfill
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: New Maintenance Ticket */}
      {showTicketModal && (
        <div className="modal-backdrop" onClick={() => setShowTicketModal(false)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <h3>Log Maintenance & Repair Ticket</h3>
            <form onSubmit={handleCreateTicket} className="stack">
              <label>
                Select Device *
                <select
                  value={newTicket.device_id}
                  onChange={(e) => setNewTicket({ ...newTicket, device_id: e.target.value })}
                  required
                >
                  <option value="">-- Choose a device --</option>
                  {devices.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.device_name} ({d.serial_number}) - {d.status}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Issue Summary *
                <input
                  type="text"
                  value={newTicket.issue_title}
                  onChange={(e) => setNewTicket({ ...newTicket, issue_title: e.target.value })}
                  placeholder="e.g. Cracked screen, battery drain, touch unresponsive"
                  required
                />
              </label>
              <div className="grid-2">
                <label>
                  Priority
                  <select
                    value={newTicket.priority}
                    onChange={(e) => setNewTicket({ ...newTicket, priority: e.target.value })}
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="critical">Critical</option>
                  </select>
                </label>
                <label>
                  Repair Vendor
                  <input
                    type="text"
                    value={newTicket.vendor_name}
                    onChange={(e) => setNewTicket({ ...newTicket, vendor_name: e.target.value })}
                    placeholder="e.g. Authorized service center"
                  />
                </label>
              </div>
              <div className="grid-2">
                <label>
                  Estimated Cost ($)
                  <input
                    type="number"
                    step="0.01"
                    value={newTicket.estimated_cost}
                    onChange={(e) => setNewTicket({ ...newTicket, estimated_cost: parseFloat(e.target.value) || 0 })}
                  />
                </label>
                <label>
                  Sent Date
                  <input
                    type="date"
                    value={newTicket.sent_date}
                    onChange={(e) => setNewTicket({ ...newTicket, sent_date: e.target.value })}
                  />
                </label>
              </div>
              <label>
                Issue Details
                <textarea
                  rows="3"
                  value={newTicket.issue_description}
                  onChange={(e) => setNewTicket({ ...newTicket, issue_description: e.target.value })}
                  placeholder="Describe hardware symptoms or diagnostics..."
                />
              </label>
              <div className="actions" style={{ marginTop: "1rem", justifyContent: "flex-end" }}>
                <button className="btn ghost" type="button" onClick={() => setShowTicketModal(false)}>
                  Cancel
                </button>
                <button className="btn primary" type="submit">
                  Log Ticket & Mark In-Repair
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Update Ticket */}
      {updateTicketTarget && (
        <div className="modal-backdrop" onClick={() => setUpdateTicketTarget(null)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <h3>Update Repair Ticket: {updateTicketTarget.issue_title}</h3>
            <form onSubmit={handleUpdateTicket} className="stack">
              <label>
                Status
                <select
                  value={ticketUpdateForm.repair_status}
                  onChange={(e) => setTicketUpdateForm({ ...ticketUpdateForm, repair_status: e.target.value })}
                >
                  <option value="in_repair">In Repair</option>
                  <option value="waiting_parts">Waiting for Parts</option>
                  <option value="completed">Completed (Restores Device to Active)</option>
                  <option value="unrepairable">Unrepairable (Marks Device as Retired)</option>
                </select>
              </label>
              <div className="grid-2">
                <label>
                  Actual Cost ($)
                  <input
                    type="number"
                    step="0.01"
                    value={ticketUpdateForm.actual_cost}
                    onChange={(e) => setTicketUpdateForm({ ...ticketUpdateForm, actual_cost: parseFloat(e.target.value) || 0 })}
                  />
                </label>
                <label>
                  Completion Date
                  <input
                    type="date"
                    value={ticketUpdateForm.completed_date}
                    onChange={(e) => setTicketUpdateForm({ ...ticketUpdateForm, completed_date: e.target.value })}
                  />
                </label>
              </div>
              <label>
                Technician Notes
                <textarea
                  rows="3"
                  value={ticketUpdateForm.technician_notes}
                  onChange={(e) => setTicketUpdateForm({ ...ticketUpdateForm, technician_notes: e.target.value })}
                  placeholder="Parts replaced, warranty info, vendor invoice number..."
                />
              </label>
              <div className="actions" style={{ marginTop: "1rem", justifyContent: "flex-end" }}>
                <button className="btn ghost" type="button" onClick={() => setUpdateTicketTarget(null)}>
                  Cancel
                </button>
                <button className="btn primary" type="submit">
                  Save Changes
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Extend Return Date */}
      {extendTarget && (
        <div className="modal-backdrop" onClick={() => setExtendTarget(null)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <h3>Extend Return Date</h3>
            <p className="muted">Device: <strong>{extendTarget.device_name}</strong> ({extendTarget.serial_number})</p>
            <form onSubmit={handleExtendReturn} className="stack">
              <label>
                New Return Date *
                <input
                  type="date"
                  value={extendForm.new_return_date}
                  onChange={(e) => setExtendForm({ ...extendForm, new_return_date: e.target.value })}
                  required
                />
              </label>
              <label>
                Reason for Extension
                <input
                  type="text"
                  value={extendForm.extension_reason}
                  onChange={(e) => setExtendForm({ ...extendForm, extension_reason: e.target.value })}
                  placeholder="e.g. Additional regression test cycle required"
                />
              </label>
              <div className="actions" style={{ marginTop: "1rem", justifyContent: "flex-end" }}>
                <button className="btn ghost" type="button" onClick={() => setExtendTarget(null)}>
                  Cancel
                </button>
                <button className="btn primary" type="submit">
                  Confirm Extension
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Process Return */}
      {returnTarget && (
        <div className="modal-backdrop" onClick={() => setReturnTarget(null)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <h3>Process Device Return & Check-in</h3>
            <p className="muted">
              Device: <strong>{returnTarget.device_name}</strong> | Returning from: <strong>{returnTarget.assigned_user_name || returnTarget.issued_to}</strong>
            </p>
            <form onSubmit={handleProcessReturn} className="stack">
              <label>
                Physical Condition on Return
                <select
                  value={returnForm.condition}
                  onChange={(e) => setReturnForm({ ...returnForm, condition: e.target.value })}
                >
                  <option value="Good / Flawless">Good / Flawless</option>
                  <option value="Normal Wear">Normal Wear & Tear</option>
                  <option value="Minor Scratches">Minor Scratches</option>
                  <option value="Damaged - Needs Repair">Damaged - Needs Repair</option>
                </select>
              </label>
              <label>
                Return Notes / Checklist
                <textarea
                  rows="3"
                  value={returnForm.return_notes}
                  onChange={(e) => setReturnForm({ ...returnForm, return_notes: e.target.value })}
                  placeholder="Charger received, device factory reset verified, SIM card removed..."
                />
              </label>
              <div className="actions" style={{ marginTop: "1rem", justifyContent: "flex-end" }}>
                <button className="btn ghost" type="button" onClick={() => setReturnTarget(null)}>
                  Cancel
                </button>
                <button className="btn primary" type="submit">
                  Confirm Check-in & Release
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Clearance Receipt */}
      {clearanceSlip && (
        <div className="modal-backdrop" onClick={() => setClearanceSlip(null)}>
          <div className="modal-box clearance-slip" onClick={(e) => e.stopPropagation()}>
            <div className="receipt-header">
              <h3>DeviceVault - Asset Return Clearance Receipt</h3>
              <p className="small-muted">Reference #{Math.floor(100000 + Math.random() * 900000)}</p>
            </div>
            <div className="receipt-body">
              <div className="kv-row">
                <span>Device Name:</span>
                <strong>{clearanceSlip.device.device_name}</strong>
              </div>
              <div className="kv-row">
                <span>Serial Number:</span>
                <code>{clearanceSlip.device.serial_number}</code>
              </div>
              <div className="kv-row">
                <span>Returned By:</span>
                <strong>{clearanceSlip.device.assigned_user_name || clearanceSlip.device.issued_to}</strong>
              </div>
              <div className="kv-row">
                <span>Date Received:</span>
                <strong>{clearanceSlip.returned_at}</strong>
              </div>
              <div className="kv-row">
                <span>Condition:</span>
                <strong>{clearanceSlip.condition}</strong>
              </div>
              <div className="kv-row">
                <span>Processed By:</span>
                <strong>{clearanceSlip.processed_by}</strong>
              </div>
              {clearanceSlip.notes && (
                <div className="kv-row">
                  <span>Notes:</span>
                  <span>{clearanceSlip.notes}</span>
                </div>
              )}
            </div>
            <div className="actions" style={{ marginTop: "1.5rem", justifyContent: "flex-end" }}>
              <button className="btn secondary" type="button" onClick={() => window.print()}>
                🖨️ Print Receipt
              </button>
              <button className="btn primary" type="button" onClick={() => setClearanceSlip(null)}>
                Done
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Record Audit Verification */}
      {showAuditModal && (
        <div className="modal-backdrop" onClick={() => setShowAuditModal(false)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <h3>Record Physical Device Verification</h3>
            <form onSubmit={handleRecordAudit} className="stack">
              <label>
                Select Device *
                <select
                  value={auditForm.device_id}
                  onChange={(e) => setAuditForm({ ...auditForm, device_id: e.target.value })}
                  required
                >
                  <option value="">-- Choose device to verify --</option>
                  {devices.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.device_name} ({d.serial_number}) - Location: {d.resident_location || "HQ"}
                    </option>
                  ))}
                </select>
              </label>
              <div className="grid-2">
                <label>
                  Audit Cycle
                  <input
                    type="text"
                    value={selectedCycle || auditForm.audit_cycle}
                    onChange={(e) => setSelectedCycle(e.target.value)}
                    required
                  />
                </label>
                <label>
                  Physical Status *
                  <select
                    value={auditForm.physical_status}
                    onChange={(e) => setAuditForm({ ...auditForm, physical_status: e.target.value })}
                  >
                    <option value="confirmed">Confirmed (Physically Present)</option>
                    <option value="damaged">Damaged (Needs Inspection)</option>
                    <option value="missing">Missing (Cannot Locate)</option>
                    <option value="disputed">Disputed (Serial/Tag Mismatch)</option>
                  </select>
                </label>
              </div>
              <label>
                Verified Location
                <input
                  type="text"
                  value={auditForm.verified_location}
                  onChange={(e) => setAuditForm({ ...auditForm, verified_location: e.target.value })}
                  placeholder="e.g. Server Room Rack 2 / QA Lab Desk 4"
                />
              </label>
              <label>
                Auditor Notes / Verification Evidence
                <textarea
                  rows="2"
                  value={auditForm.notes}
                  onChange={(e) => setAuditForm({ ...auditForm, notes: e.target.value })}
                  placeholder="Serial tag readable, barcode scanned, asset tag intact..."
                />
              </label>
              <div className="actions" style={{ marginTop: "1rem", justifyContent: "flex-end" }}>
                <button className="btn ghost" type="button" onClick={() => setShowAuditModal(false)}>
                  Cancel
                </button>
                <button className="btn primary" type="submit">
                  Record Verification
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </section>
  );
}
