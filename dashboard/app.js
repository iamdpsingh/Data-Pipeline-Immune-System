// ==============================================================================
// Data Pipeline Immune System — Dashboard Interactive Controller
// ==============================================================================

const mockIncidents = [
  {
    id: "inc-77f98d",
    pipeline: "orders",
    severity: "P1",
    root_cause: "UPSTREAM_PARTIAL_LOAD",
    action: "RETRY_SOURCE_EXTRACTION",
    state: "RESOLVED",
    mttr: "1.2m"
  },
  {
    id: "inc-64a21e",
    pipeline: "orders",
    severity: "P2",
    root_cause: "API_TIMEOUT",
    action: "RETRY_SOURCE_EXTRACTION",
    state: "RESOLVED",
    mttr: "0.8m"
  },
  {
    id: "inc-55c39b",
    pipeline: "orders",
    severity: "P3",
    root_cause: "SCHEMA_ADDITIVE_CHANGE",
    action: "ADD_COLUMN_TO_STAGING",
    state: "RESOLVED",
    mttr: "0.4m"
  },
  {
    id: "inc-41d88a",
    pipeline: "orders",
    severity: "P0",
    root_cause: "PII_EXPOSURE_RISK",
    action: "BLOCK_PIPELINE",
    state: "BLOCKED",
    mttr: "0.1m"
  },
  {
    id: "inc-32e70c",
    pipeline: "orders",
    severity: "P2",
    root_cause: "MISSING_PARTITION",
    action: "REPROCESS_PARTITION",
    state: "RESOLVED",
    mttr: "2.1m"
  }
];

function renderTable(incidents) {
  const tbody = document.getElementById("incidentsBody");
  tbody.innerHTML = "";

  incidents.forEach(inc => {
    const tr = document.createElement("tr");

    let sevBadge = `<span class="badge-p2">P2</span>`;
    if (inc.severity === "P0") sevBadge = `<span class="badge-p0">P0</span>`;
    if (inc.severity === "P1") sevBadge = `<span class="badge-p1">P1</span>`;
    if (inc.severity === "P3") sevBadge = `<span class="badge-p2" style="color:#cbd5e1">P3</span>`;

    const stateClass = inc.state === "BLOCKED" ? "state-blocked" : "state-resolved";

    tr.innerHTML = `
      <td class="mono">${inc.id}</td>
      <td><strong>${inc.pipeline}</strong></td>
      <td>${sevBadge}</td>
      <td class="mono" style="font-size:0.75rem">${inc.root_cause}</td>
      <td class="mono" style="font-size:0.75rem">${inc.action}</td>
      <td><span class="state-pill ${stateClass}">${inc.state}</span></td>
      <td class="mono">${inc.mttr}</td>
    `;
    tbody.appendChild(tr);
  });
}

function appendTerminalLog(msg) {
  const terminal = document.getElementById("terminalOutput");
  const timestamp = new Date().toISOString().substring(11, 19);
  terminal.textContent += `\n> [${timestamp}] ${msg}`;
  terminal.scrollTop = terminal.scrollHeight;
}

function triggerSimulation(type) {
  const badge = document.getElementById("activeIncidentBadge");
  const randomId = "inc-" + Math.random().toString(16).substring(2, 8);

  appendTerminalLog(`[INJECTION] Triggering simulated fault: ${type.toUpperCase()}`);

  if (type === "row_anomaly") {
    badge.className = "incident-badge badge-p1";
    badge.textContent = `ACTIVE INCIDENT: ${randomId} (orders - ROW_COUNT_DROP)`;
    
    setTimeout(() => {
      appendTerminalLog(`[DETECTION] Z-Score -3.4 deviation detected. Statistical drop 48%`);
    }, 400);

    setTimeout(() => {
      appendTerminalLog(`[DIAGNOSIS] Diagnosed UPSTREAM_PARTIAL_LOAD (Confidence 0.95)`);
    }, 900);

    setTimeout(() => {
      appendTerminalLog(`[RISK] Evaluated action RETRY_SOURCE_EXTRACTION: LOW RISK`);
    }, 1400);

    setTimeout(() => {
      appendTerminalLog(`[REMEDIATION] Retriggering upstream extraction sensor...`);
    }, 1900);

    setTimeout(() => {
      appendTerminalLog(`[VERIFICATION] Re-checking orders volume: 1,020 rows (PASSED)`);
    }, 2500);

    setTimeout(() => {
      appendTerminalLog(`[LEARNING] Incident ${randomId} written to incident_memory. RESOLVED.`);
      mockIncidents.unshift({
        id: randomId,
        pipeline: "orders",
        severity: "P1",
        root_cause: "UPSTREAM_PARTIAL_LOAD",
        action: "RETRY_SOURCE_EXTRACTION",
        state: "RESOLVED",
        mttr: "1.1m"
      });
      renderTable(mockIncidents);
    }, 3100);
  } else if (type === "pii_exposure") {
    badge.className = "incident-badge badge-p0";
    badge.textContent = `CRITICAL INCIDENT: ${randomId} (orders - PII_EXPOSURE)`;

    setTimeout(() => {
      appendTerminalLog(`[DETECTION] Column 'customer_ssn' detected. Matches sensitive PII regex.`);
    }, 400);

    setTimeout(() => {
      appendTerminalLog(`[RISK] NEVER-ALLOW RULE TRIGGERED: Prohibited action EXPOSE_PII_COLUMN.`);
    }, 900);

    setTimeout(() => {
      appendTerminalLog(`[CONTROLLER] HARD BLOCK ENFORCED. Pipeline execution halted immediately.`);
      mockIncidents.unshift({
        id: randomId,
        pipeline: "orders",
        severity: "P0",
        root_cause: "PII_EXPOSURE_RISK",
        action: "BLOCK_PIPELINE",
        state: "BLOCKED",
        mttr: "0.1m"
      });
      renderTable(mockIncidents);
    }, 1500);
  } else if (type === "null_spike") {
    badge.className = "incident-badge badge-p2";
    badge.textContent = `WARNING INCIDENT: ${randomId} (orders - NULL_SPIKE_25%)`;

    setTimeout(() => {
      appendTerminalLog(`[DETECTION] customer_id null ratio 0.25 breaches 0.05 threshold.`);
    }, 400);

    setTimeout(() => {
      appendTerminalLog(`[REMEDIATION] Routing 25% malformed rows to dead-letter quarantine bucket.`);
    }, 1100);

    setTimeout(() => {
      appendTerminalLog(`[VERIFICATION] Silver table clean (0 nulls). Quarantined 250 bad records.`);
      mockIncidents.unshift({
        id: randomId,
        pipeline: "orders",
        severity: "P2",
        root_cause: "NULL_SOURCE_DATA",
        action: "QUARANTINE_BAD_RECORDS",
        state: "RESOLVED",
        mttr: "0.7m"
      });
      renderTable(mockIncidents);
    }, 1800);
  } else if (type === "schema_drift") {
    badge.className = "incident-badge badge-p1";
    badge.textContent = `PENDING APPROVAL: ${randomId} (orders - BREAKING_DRIFT)`;

    setTimeout(() => {
      appendTerminalLog(`[DETECTION] Column 'amount' mutated FLOAT -> STRING.`);
    }, 400);

    setTimeout(() => {
      appendTerminalLog(`[RISK] HIGH RISK ACTION. Automation blocked. Approval requested on dashboard.`);
    }, 900);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  renderTable(mockIncidents);

  const filterInput = document.getElementById("tableFilter");
  if (filterInput) {
    filterInput.addEventListener("input", (e) => {
      const q = e.target.value.toLowerCase();
      const filtered = mockIncidents.filter(i => 
        i.id.toLowerCase().includes(q) ||
        i.pipeline.toLowerCase().includes(q) ||
        i.root_cause.toLowerCase().includes(q) ||
        i.action.toLowerCase().includes(q)
      );
      renderTable(filtered);
    });
  }

  const sweepBtn = document.getElementById("btnTriggerScan");
  if (sweepBtn) {
    sweepBtn.addEventListener("click", () => {
      appendTerminalLog("[SCAN] Performing full immune sweep across all 12 pipelines...");
      setTimeout(() => {
        appendTerminalLog("[SCAN] All 12 pipelines nominal. Zero unhandled anomalies.");
      }, 1000);
    });
  }
});
