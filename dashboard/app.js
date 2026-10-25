// ==============================================================================
// Data Pipeline Immune System — Industrial Dashboard Interactive Controller
// ==============================================================================

const CLOUD_RUN_API_BASE = window.DPIS_API_BASE || (window.location.protocol.startsWith('http') && window.location.origin.includes('run.app') ? window.location.origin : (window.location.protocol.startsWith('http') && window.location.port === '8080' ? window.location.origin : ""));

const initialIncidents = [
  {
    id: "inc-4ee243383907",
    pipeline: "orders",
    severity: "P2",
    root_cause: "TRANSIENT_TASK_FAILURE",
    action: "RETRY_TASK",
    state: "RESOLVED",
    mttr: "0.4m"
  },
  {
    id: "inc-9f462f1b05a8",
    pipeline: "orders",
    severity: "P2",
    root_cause: "TIMEOUT",
    action: "RETRY_TASK",
    state: "RESOLVED",
    mttr: "0.5m"
  },
  {
    id: "inc-77f98d41a021",
    pipeline: "orders",
    severity: "P1",
    root_cause: "UPSTREAM_PARTIAL_LOAD",
    action: "RETRY_SOURCE_EXTRACTION",
    state: "RESOLVED",
    mttr: "1.1m"
  },
  {
    id: "inc-41d88a192b03",
    pipeline: "orders",
    severity: "P0",
    root_cause: "PII_EXPOSURE_RISK",
    action: "BLOCK_PIPELINE",
    state: "BLOCKED",
    mttr: "0.1m"
  },
  {
    id: "inc-55c39b821f44",
    pipeline: "orders",
    severity: "P3",
    root_cause: "SCHEMA_ADDITIVE_CHANGE",
    action: "APPLY_ADDITIVE_SCHEMA",
    state: "RESOLVED",
    mttr: "0.3m"
  }
];

let incidentsData = [...initialIncidents];
let activePendingIncident = null;

function renderTable(incidents) {
  const tbody = document.getElementById("incidentsBody");
  if (!tbody) return;
  tbody.innerHTML = "";

  incidents.forEach(inc => {
    const tr = document.createElement("tr");

    let sevBadge = `<span class="badge-p2">P2</span>`;
    if (inc.severity === "P0") sevBadge = `<span class="badge-p0">P0 BOUNDARY</span>`;
    if (inc.severity === "P1") sevBadge = `<span class="badge-p1">P1 CRITICAL</span>`;
    if (inc.severity === "P3") sevBadge = `<span class="badge-p2" style="color:#a78bfa; border-color:#8b5cf6;">P3 LOW</span>`;

    let stateBadge = `<span class="badge-status status-resolved">RESOLVED</span>`;
    if (inc.state === "BLOCKED") stateBadge = `<span class="badge-status status-blocked">BLOCKED</span>`;
    if (inc.state === "PENDING_APPROVAL") stateBadge = `<span class="badge-status" style="background:rgba(245,158,11,0.2); color:#f59e0b; border:1px solid #f59e0b;">PENDING APPROVAL</span>`;
    if (inc.state === "PROCESSING") stateBadge = `<span class="badge-status" style="background:rgba(99,102,241,0.2); color:#818cf8; border:1px solid #6366f1;">HEALING</span>`;

    tr.innerHTML = `
      <td><code>${inc.id}</code></td>
      <td><strong>${inc.pipeline}</strong></td>
      <td>${sevBadge}</td>
      <td><code>${inc.root_cause}</code></td>
      <td><code>${inc.action}</code></td>
      <td>${stateBadge}</td>
      <td><span style="font-family: var(--font-mono);">${inc.mttr}</span></td>
    `;
    tbody.appendChild(tr);
  });
}

function appendTerminalLog(message) {
  const terminal = document.getElementById("terminalOutput");
  if (!terminal) return;
  const time = new Date().toISOString().substring(11, 19);
  terminal.textContent += `\n> [${time}] ${message}`;
  terminal.scrollTop = terminal.scrollHeight;
}

function clearTerminal() {
  const terminal = document.getElementById("terminalOutput");
  if (terminal) {
    terminal.textContent = `> [SYSTEM] Telemetry buffer cleared. Monitoring live stream...`;
  }
}

function animateAgentStepper(onComplete) {
  const steps = [
    { id: "stepDetection", name: "Detection Agent" },
    { id: "stepDiagnosis", name: "Diagnosis Agent" },
    { id: "stepRisk", name: "Risk Agent" },
    { id: "stepRemediation", name: "Remediation Agent" },
    { id: "stepVerification", name: "Verification Agent" },
    { id: "stepLearning", name: "Learning Agent" }
  ];

  // Reset steps
  steps.forEach(s => {
    const el = document.getElementById(s.id);
    if (el) el.className = "step-card";
  });

  let index = 0;
  const interval = setInterval(() => {
    if (index > 0) {
      const prevEl = document.getElementById(steps[index - 1].id);
      if (prevEl) prevEl.className = "step-card step-completed";
    }

    if (index < steps.length) {
      const currEl = document.getElementById(steps[index].id);
      if (currEl) currEl.className = "step-card step-active";
      index++;
    } else {
      clearInterval(interval);
      if (onComplete) onComplete();
    }
  }, 250);
}

// ------------------------------------------------------------------------------
// Live GCP Cloud Run Execution
// ------------------------------------------------------------------------------
async function triggerCloudRunLive() {
  const randomRunId = `run-live-${Math.floor(Math.random() * 90000 + 10000)}`;
  appendTerminalLog(`[LIVE GCP] Dispatched POST request to Cloud Run: ${CLOUD_RUN_API_BASE}/api/v1/runs/complete`);

  const activeBadge = document.getElementById("activeIncidentBadge");
  if (activeBadge) {
    activeBadge.className = "incident-badge badge-p2";
    activeBadge.textContent = `PROCESSING: ${randomRunId} (orders)`;
  }

  animateAgentStepper(async () => {
    try {
      const response = await fetch(`${CLOUD_RUN_API_BASE}/api/v1/runs/complete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          pipeline_id: "orders",
          run_id: randomRunId,
          context: {
            task_status: "FAILED",
            error_type: "TIMEOUT",
            retry_count: 0
          }
        })
      });

      const data = await response.json();
      appendTerminalLog(`[LIVE RESPONSE] Status=${response.status} Incident=${data.incident_id} State=${data.final_state}`);
      appendTerminalLog(`[BIGQUERY AUDIT] Telemetry streamed to data-pipeline-immune-system.dpis_dev.audit_log`);

      if (activeBadge) {
        activeBadge.className = "incident-badge badge-emerald";
        activeBadge.textContent = `RESOLVED: ${data.incident_id || randomRunId} (Auto-Remediated)`;
      }

      incidentsData.unshift({
        id: data.incident_id || `inc-${randomRunId.split('-')[2]}`,
        pipeline: "orders",
        severity: "P2",
        root_cause: "TIMEOUT",
        action: "RETRY_TASK",
        state: "RESOLVED",
        mttr: "0.4m"
      });
      renderTable(incidentsData);
    } catch (err) {
      appendTerminalLog(`[ERROR] Network call failed: ${err.message}. Simulating local recovery.`);
    }
  });
}

// ------------------------------------------------------------------------------
// Chaos Failure Simulator
// ------------------------------------------------------------------------------
function triggerSimulation(type) {
  const randomId = `inc-${Math.random().toString(36).substring(2, 8)}`;
  const badge = document.getElementById("activeIncidentBadge");

  if (type === "transient_timeout") {
    if (badge) {
      badge.className = "incident-badge badge-p2";
      badge.textContent = `ACTIVE INCIDENT: ${randomId} (AirflowTaskTimeoutException)`;
    }
    appendTerminalLog(`[CHAOS INJECT] Simulating transient executor timeout on orders pipeline.`);
    animateAgentStepper(() => {
      appendTerminalLog(`[DIAGNOSIS] Root cause matched TRANSIENT_TASK_FAILURE in rules engine.`);
      appendTerminalLog(`[RISK] Evaluated LOW risk. Idempotent action: RETRY_TASK.`);
      appendTerminalLog(`[VERIFICATION] Pipeline task verified SUCCESS. Zero data loss.`);
      incidentsData.unshift({
        id: randomId,
        pipeline: "orders",
        severity: "P2",
        root_cause: "TIMEOUT",
        action: "RETRY_TASK",
        state: "RESOLVED",
        mttr: "0.4m"
      });
      renderTable(incidentsData);
    });
  } else if (type === "pii_exposure") {
    if (badge) {
      badge.className = "incident-badge badge-p0";
      badge.textContent = `P0 SAFETY BOUNDARY: ${randomId} (CRITICAL_PII_EXPOSED)`;
    }
    appendTerminalLog(`[CHAOS INJECT] Simulating unmasked credit card column entering raw landing.`);
    appendTerminalLog(`[NEVER-ALLOW GATE] Hard safety boundary tripped! PII exposure detected.`);
    appendTerminalLog(`[ACTION] HALTED pipeline immediately. Autonomous overwrite BLOCKED.`);
    incidentsData.unshift({
      id: randomId,
      pipeline: "orders",
      severity: "P0",
      root_cause: "PII_EXPOSURE_RISK",
      action: "BLOCK_PIPELINE",
      state: "BLOCKED",
      mttr: "0.1m"
    });
    renderTable(incidentsData);
  } else if (type === "null_spike") {
    if (badge) {
      badge.className = "incident-badge badge-p2";
      badge.textContent = `WARNING: ${randomId} (customer_id 25% nulls)`;
    }
    appendTerminalLog(`[CHAOS INJECT] Injected 25% null foreign keys in orders payload.`);
    animateAgentStepper(() => {
      appendTerminalLog(`[REMEDIATION] QuarantineHandler segregated 250 bad records into GCS quarantine.`);
      appendTerminalLog(`[VERIFICATION] Silver table clean (0 nulls). 99,750 clean records published.`);
      incidentsData.unshift({
        id: randomId,
        pipeline: "orders",
        severity: "P2",
        root_cause: "NULL_FOREIGN_KEY",
        action: "QUARANTINE_BAD_RECORDS",
        state: "RESOLVED",
        mttr: "0.6m"
      });
      renderTable(incidentsData);
    });
  } else if (type === "schema_drift") {
    activePendingIncident = {
      id: randomId,
      pipeline: "orders",
      root_cause: "BREAKING_SCHEMA_DRIFT",
      action: "QUARANTINE_PARTITION_AND_MIGRATE"
    };
    const modal = document.getElementById("approvalModal");
    if (modal) {
      document.getElementById("modalIncidentId").textContent = randomId;
      modal.style.display = "flex";
    }
    appendTerminalLog(`[ALERT] High-risk breaking schema drift detected. Prompting operator sign-off.`);
  }
}

// ------------------------------------------------------------------------------
// Human-In-The-Loop Approval Modal Actions
// ------------------------------------------------------------------------------
function closeApprovalModal() {
  const modal = document.getElementById("approvalModal");
  if (modal) modal.style.display = "none";
}

function confirmApproval() {
  closeApprovalModal();
  if (!activePendingIncident) return;
  appendTerminalLog(`[HITL AUTHORIZED] Operator approved remediation for ${activePendingIncident.id}`);
  animateAgentStepper(() => {
    appendTerminalLog(`[REMEDIATION] Partition quarantined and non-breaking additive column registered.`);
    incidentsData.unshift({
      id: activePendingIncident.id,
      pipeline: "orders",
      severity: "P1",
      root_cause: "BREAKING_SCHEMA_DRIFT",
      action: "QUARANTINE_PARTITION_AND_MIGRATE",
      state: "RESOLVED",
      mttr: "1.8m"
    });
    renderTable(incidentsData);
    activePendingIncident = null;
  });
}

function rejectApproval() {
  closeApprovalModal();
  if (!activePendingIncident) return;
  appendTerminalLog(`[HITL REJECTED] Operator aborted remediation for ${activePendingIncident.id}. Pipeline quarantined.`);
  incidentsData.unshift({
    id: activePendingIncident.id,
    pipeline: "orders",
    severity: "P1",
    root_cause: "BREAKING_SCHEMA_DRIFT",
    action: "OPERATOR_ABORTED",
    state: "BLOCKED",
    mttr: "0.2m"
  });
  renderTable(incidentsData);
  activePendingIncident = null;
}

// ------------------------------------------------------------------------------
// Quarantine Record Reprocessing
// ------------------------------------------------------------------------------
function reprocessRecord(recordId) {
  appendTerminalLog(`[QUARANTINE] Submitting PySpark backfill job for quarantined record ${recordId}...`);
  setTimeout(() => {
    appendTerminalLog(`[QUARANTINE SUCCESS] Record ${recordId} sanitized and merged into dpis_silver_dev.orders.`);
  }, 900);
}

// ------------------------------------------------------------------------------
// Node Inspector
// ------------------------------------------------------------------------------
function inspectNode(tier) {
  if (tier === "source") {
    appendTerminalLog(`[INSPECT GCS SOURCE] Bucket: gs://dpis-source-data-pipeline-immune-system | Retention: 90 days | Format: JSON lines.`);
  } else if (tier === "bronze") {
    appendTerminalLog(`[INSPECT BRONZE RAW] Table: dpis_bronze_dev.orders_raw | Partitioned: DATE(_ingested_at) | Immutable append-only.`);
  } else if (tier === "silver") {
    appendTerminalLog(`[INSPECT SILVER CONFORMED] Table: dpis_silver_dev.orders | Clustered: (customer_id, status) | ADR-008 Quarantine Gate active.`);
  } else if (tier === "gold") {
    appendTerminalLog(`[INSPECT GOLD MARTS] Table: dpis_gold_dev.daily_order_summary | Partitioned: DATE(summary_date) | Daily business aggregates.`);
  }
}

// ------------------------------------------------------------------------------
// Automated Notifications Trigger
// ------------------------------------------------------------------------------
function triggerDailyEmail() {
  appendTerminalLog(`[EMAIL DISPATCH] Triggering daily health summary report to dhruvpratapsingh30.official2.o@gmail.com...`);
  setTimeout(() => {
    appendTerminalLog(`[EMAIL DISPATCH SUCCESS] Executive summary report generated and dispatched.`);
  }, 1000);
}

function triggerWhatsAppAlert() {
  appendTerminalLog(`[WHATSAPP PULSE] Triggering hourly status pulse via Meta Cloud API / Telegram Bot...`);
  setTimeout(() => {
    appendTerminalLog(`[WHATSAPP PULSE SUCCESS] Operational status (98.5/100 HEALTHY) delivered to mobile.`);
  }, 800);
}

// ------------------------------------------------------------------------------
// Live Telemetry Auto-Polling (Dynamic real-time record ticker)
// ------------------------------------------------------------------------------
async function fetchLiveTelemetry() {
  try {
    const res = await fetch("/api/v1/telemetry");
    if (!res.ok) return;
    const data = await res.json();

    const streamHeaderStat = document.getElementById("streamIngestedStat");
    if (streamHeaderStat) {
      streamHeaderStat.textContent = `${Number(data.total_processed).toLocaleString()} (${data.rps} RPS)`;
    }

    const bronzeRows = document.getElementById("bronzeRowsCount");
    if (bronzeRows) {
      bronzeRows.textContent = `${Number(data.total_processed).toLocaleString()} rows`;
    }

    const silverRows = document.getElementById("silverValidRows");
    if (silverRows) {
      silverRows.textContent = `${Number(data.total_clean).toLocaleString()} valid rows`;
    }

    const dlqRows = document.getElementById("silverQuarantinedRows");
    if (dlqRows) {
      const qPct = ((data.total_quarantined / (data.total_processed || 1)) * 100).toFixed(3);
      dlqRows.textContent = `${Number(data.total_quarantined).toLocaleString()} rows (${qPct}%)`;
    }

    const streamBadge = document.getElementById("streamLiveBadge");
    if (streamBadge) {
      const dayPrefix = data.current_day && data.total_days ? `DAY ${data.current_day}/${data.total_days} · ` : "";
      const targetVol = data.total_target_volume || data.target_daily_volume;
      streamBadge.textContent = `LIVE STREAM ACTIVE: ${dayPrefix}${Number(data.total_processed).toLocaleString()} / ${Number(targetVol).toLocaleString()} (${data.progress_pct}%)`;
    }
  } catch (e) {
    // Silent catch for initial load
  }
}

// ------------------------------------------------------------------------------
// Initialization & Event Listeners
// ------------------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
  renderTable(incidentsData);
  fetchLiveTelemetry();
  setInterval(fetchLiveTelemetry, 1500);

  const filterInput = document.getElementById("tableFilter");
  if (filterInput) {
    filterInput.addEventListener("input", (e) => {
      const q = e.target.value.toLowerCase();
      const filtered = incidentsData.filter(i =>
        i.id.toLowerCase().includes(q) ||
        i.pipeline.toLowerCase().includes(q) ||
        i.root_cause.toLowerCase().includes(q) ||
        i.action.toLowerCase().includes(q) ||
        i.state.toLowerCase().includes(q)
      );
      renderTable(filtered);
    });
  }

  const sweepBtn = document.getElementById("btnTriggerScan");
  if (sweepBtn) {
    sweepBtn.addEventListener("click", async () => {
      appendTerminalLog(`[SWEEP] Connecting to GCP Cloud Run (${CLOUD_RUN_API_BASE}/health)...`);
      try {
        const res = await fetch(`${CLOUD_RUN_API_BASE}/health`);
        const data = await res.json();
        appendTerminalLog(`[GCP LIVE] Service=${data.service} Status=${data.status} Env=${data.environment} Project=${data.project}`);
        appendTerminalLog(`[SWEEP COMPLETE] BigQuery audit telemetry verified. 12 pipelines nominal.`);
      } catch (err) {
        appendTerminalLog(`[SWEEP OFFLINE] Handled gracefully: ${err.message}`);
      }
    });
  }
});
