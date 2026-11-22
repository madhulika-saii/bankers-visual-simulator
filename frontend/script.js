/**
 * Banker's Algorithm Visualizer - SaaS Operating Systems Engine
 * Features:
 * - Dynamic process & resource configuration (1..10 processes, 1..10 resources)
 * - Preset configurations (3x2, 5x3, 6x4)
 * - Large SVG Resource Allocation Graph (Solid blue: Resource -> Process; Dashed orange: Process -> Resource)
 * - Pan, Zoom, Fit-to-screen, and Reset graph controls
 * - Dynamic Allocation, Maximum, Need matrices, and Available vector
 * - Interactive request and release with C backend validation and rollback
 * - Step-by-step safe sequence visual animation with Play, Pause, Restart, and Reset
 * - Execution log deduplication and severity styling
 */

const API = "/api";
const $ = (id) => document.getElementById(id);
const NS = "http://www.w3.org/2000/svg";

let simulation = null;
let previousSimulation = null;
let temporaryRequest = null;

// Graph pan & zoom transform state
const graphView = {
    x: 0,
    y: 0,
    scale: 1,
    minScale: 0.35,
    maxScale: 3.0,
    isPanning: false,
    startX: 0,
    startY: 0
};

// Safe sequence animation player state
const animPlayer = {
    timer: null,
    isPlaying: false,
    stepIndex: 0,
    sequence: [],
    workVector: []
};

// Built-in presets
const PRESETS = {
    "3x2": {
        processes: 3,
        resources: 2,
        total: [5, 5],
        allocation: [
            [1, 1],
            [2, 1],
            [1, 2]
        ],
        maximum: [
            [2, 2],
            [2, 2],
            [3, 3]
        ]
    },
    "5x3": {
        processes: 5,
        resources: 3,
        total: [10, 5, 7],
        allocation: [
            [0, 1, 0],
            [2, 0, 0],
            [3, 0, 2],
            [2, 1, 1],
            [0, 0, 2]
        ],
        maximum: [
            [7, 5, 3],
            [3, 2, 2],
            [9, 0, 2],
            [2, 2, 2],
            [4, 3, 3]
        ]
    },
    "6x4": {
        processes: 6,
        resources: 4,
        total: [12, 9, 10, 8],
        allocation: [
            [1, 1, 0, 1],
            [2, 0, 1, 1],
            [3, 1, 2, 1],
            [1, 2, 1, 0],
            [1, 0, 1, 1],
            [1, 1, 1, 1]
        ],
        maximum: [
            [3, 2, 1, 2],
            [4, 1, 2, 2],
            [4, 2, 3, 2],
            [2, 3, 2, 1],
            [3, 2, 2, 2],
            [2, 2, 2, 2]
        ]
    }
};

// ==========================================================================
// API Helper
// ==========================================================================
async function apiCall(endpoint, method = "GET", body = null) {
    const options = { method, headers: {} };
    if (body !== null) {
        options.headers["Content-Type"] = "application/json";
        options.body = JSON.stringify(body);
    }

    const response = await fetch(`${API}${endpoint}`, options);
    const result = await response.json();

    if (!response.ok) {
        throw new Error(result.error || result.message || "API request failed");
    }

    return result;
}

// ==========================================================================
// Execution Log Helper
// ==========================================================================
let lastLoggedMessage = "";
let lastLoggedTime = 0;

function log(message, type = "info") {
    const area = $("executionLog");
    if (!area) return;

    const now = Date.now();
    // Collapse identical messages that occur within 3 seconds
    if (message === lastLoggedMessage && (now - lastLoggedTime) < 3000) {
        const firstLine = area.firstElementChild;
        if (firstLine) {
            const count = Number(firstLine.dataset.count || 1) + 1;
            firstLine.dataset.count = count;
            firstLine.textContent = `[${new Date().toLocaleTimeString()}] ${message} (x${count})`;
            lastLoggedTime = now;
            return;
        }
    }

    lastLoggedMessage = message;
    lastLoggedTime = now;

    const line = document.createElement("div");
    line.className = `log-line log-${type}`;
    line.dataset.count = 1;
    line.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
    area.prepend(line);

    while (area.children.length > 40) {
        area.removeChild(area.lastChild);
    }
}

// ==========================================================================
// Configuration Grid Renderers
// ==========================================================================
function renderConfigInputs(n, m, defaultData = null) {
    // 1. Total instances row
    const totalWrap = $("totalInstancesContainer");
    totalWrap.innerHTML = "";
    for (let j = 0; j < m; j++) {
        const item = document.createElement("div");
        item.className = "vector-field-item";
        const val = defaultData && defaultData.total && defaultData.total[j] !== undefined
            ? defaultData.total[j] : 10;
        item.innerHTML = `<span class="vector-field-label">R${j}</span>
                          <input type="number" min="0" max="99" id="cfgTotal_${j}" class="vector-field-input" value="${val}">`;
        totalWrap.appendChild(item);
    }

    // 2. Allocation Table
    const allocWrap = $("allocInputsContainer");
    let allocHtml = `<table><thead><tr><th>Proc</th>`;
    for (let j = 0; j < m; j++) allocHtml += `<th>R${j}</th>`;
    allocHtml += `</tr></thead><tbody>`;

    for (let i = 0; i < n; i++) {
        allocHtml += `<tr><th>P${i}</th>`;
        for (let j = 0; j < m; j++) {
            const val = defaultData && defaultData.allocation && defaultData.allocation[i] && defaultData.allocation[i][j] !== undefined
                ? defaultData.allocation[i][j] : 0;
            allocHtml += `<td><input type="number" min="0" max="99" id="cfgAlloc_${i}_${j}" value="${val}"></td>`;
        }
        allocHtml += `</tr>`;
    }
    allocHtml += `</tbody></table>`;
    allocWrap.innerHTML = allocHtml;

    // 3. Maximum Table
    const maxWrap = $("maxInputsContainer");
    let maxHtml = `<table><thead><tr><th>Proc</th>`;
    for (let j = 0; j < m; j++) maxHtml += `<th>R${j}</th>`;
    maxHtml += `</tr></thead><tbody>`;

    for (let i = 0; i < n; i++) {
        maxHtml += `<tr><th>P${i}</th>`;
        for (let j = 0; j < m; j++) {
            const val = defaultData && defaultData.maximum && defaultData.maximum[i] && defaultData.maximum[i][j] !== undefined
                ? defaultData.maximum[i][j] : 2;
            maxHtml += `<td><input type="number" min="0" max="99" id="cfgMax_${i}_${j}" value="${val}"></td>`;
        }
        maxHtml += `</tr>`;
    }
    maxHtml += `</tbody></table>`;
    maxWrap.innerHTML = maxHtml;
}

function readConfigInputs() {
    const n = Number($("numProcessesInput").value);
    const m = Number($("numResourcesInput").value);

    const total = [];
    for (let j = 0; j < m; j++) {
        total.push(Number($(`cfgTotal_${j}`).value));
    }

    const allocation = [];
    const maximum = [];

    for (let i = 0; i < n; i++) {
        const aRow = [];
        const mRow = [];
        for (let j = 0; j < m; j++) {
            aRow.push(Number($(`cfgAlloc_${i}_${j}`).value));
            mRow.push(Number($(`cfgMax_${i}_${j}`).value));
        }
        allocation.push(aRow);
        maximum.push(mRow);
    }

    return { processes: n, resources: m, total, allocation, maximum };
}

// ==========================================================================
// Dashboard Update
// ==========================================================================
function updateDashboard(state) {
    previousSimulation = simulation;
    simulation = state;

    $("availableValues").textContent = `[ ${state.available.join("  |  ")} ]`;

    // Render Allocation, Maximum, and Need Matrices
    $("allocationMatrix").innerHTML = createMatrixTable(
        state.allocation, "Allocation", previousSimulation ? previousSimulation.allocation : null
    );

    if ($("maximumMatrix")) {
        $("maximumMatrix").innerHTML = createMatrixTable(
            state.maximum, "Maximum", previousSimulation ? previousSimulation.maximum : null
        );
    }

    $("needMatrix").innerHTML = createMatrixTable(
        state.need, "Need", previousSimulation ? previousSimulation.need : null
    );

    // Dynamic Selectors for Operations
    updateOperationInputs(state.processes, state.resources);

    // Sync input spinners
    $("numProcessesInput").value = state.processes;
    $("numResourcesInput").value = state.resources;

    // Re-render Graph
    renderGraph();
}

// Build matrix table HTML with changed-value highlighting
function createMatrixTable(matrix, title, prevMatrix) {
    let html = `<table><thead><tr><th>${title}</th>`;
    for (let j = 0; j < simulation.resources; j++) {
        html += `<th class="th-resource">R${j}</th>`;
    }
    html += "</tr></thead><tbody>";

    matrix.forEach((row, i) => {
        html += `<tr><th class="th-process">P${i}</th>`;
        row.forEach((value, j) => {
            const isChanged = prevMatrix && prevMatrix[i] && prevMatrix[i][j] !== value;
            const changedClass = isChanged ? "cell-changed" : "";
            html += `<td class="${changedClass}">${value}</td>`;
        });
        html += "</tr>";
    });

    html += "</tbody></table>";
    return html;
}

// Update Interactive Request & Release Inputs
function updateOperationInputs(numProcesses, numResources) {
    // Process Dropdowns
    const reqSel = $("requestProcess");
    const relSel = $("releaseProcess");

    [reqSel, relSel].forEach(sel => {
        if (!sel) return;
        const currentVal = sel.value;
        sel.innerHTML = "";
        for (let i = 0; i < numProcesses; i++) {
            const opt = document.createElement("option");
            opt.value = i;
            opt.textContent = `P${i}`;
            if (String(i) === String(currentVal)) opt.selected = true;
            sel.appendChild(opt);
        }
    });

    // Request Vector Fields
    const reqWrap = $("requestVectorContainer");
    reqWrap.innerHTML = "";
    for (let j = 0; j < numResources; j++) {
        const item = document.createElement("div");
        item.className = "vector-field-item";
        item.innerHTML = `<span class="vector-field-label">R${j}</span>
                          <input type="number" min="0" id="reqVal_${j}" class="vector-field-input" value="0">`;
        reqWrap.appendChild(item);
    }

    // Release Vector Fields
    const relWrap = $("releaseVectorContainer");
    relWrap.innerHTML = "";
    for (let j = 0; j < numResources; j++) {
        const item = document.createElement("div");
        item.className = "vector-field-item";
        item.innerHTML = `<span class="vector-field-label">R${j}</span>
                          <input type="number" min="0" id="relVal_${j}" class="vector-field-input" value="0">`;
        relWrap.appendChild(item);
    }
}

// ==========================================================================
// SVG Element Helpers
// ==========================================================================
function svgElement(tag, attributes = {}) {
    const element = document.createElementNS(NS, tag);
    Object.entries(attributes).forEach(([key, value]) => {
        element.setAttribute(key, value);
    });
    return element;
}

function addText(svg, x, y, value, className) {
    const text = svgElement("text", {
        x, y,
        class: className,
        "text-anchor": "middle"
    });
    text.textContent = value;
    svg.appendChild(text);
}

// ==========================================================================
// Render Resource Allocation Graph (Hero Visual Element)
// ==========================================================================
function renderGraph() {
    if (!simulation) return;

    const svg = $("resourceGraph");
    svg.replaceChildren();

    const defs = svgElement("defs");

    // Allocation Arrow Marker (Solid Blue: Resource -> Process)
    const allocMarker = svgElement("marker", {
        id: "allocationArrow",
        markerWidth: 9,
        markerHeight: 9,
        refX: 7,
        refY: 3.5,
        orient: "auto"
    });
    allocMarker.appendChild(svgElement("path", {
        d: "M0,0 L0,7 L7,3.5 z",
        fill: "#2563EB"
    }));

    // Request Arrow Marker (Dashed Orange: Process -> Resource)
    const reqMarker = svgElement("marker", {
        id: "requestArrow",
        markerWidth: 9,
        markerHeight: 9,
        refX: 7,
        refY: 3.5,
        orient: "auto"
    });
    reqMarker.appendChild(svgElement("path", {
        d: "M0,0 L0,7 L7,3.5 z",
        fill: "#EA580C"
    }));

    defs.appendChild(allocMarker);
    defs.appendChild(reqMarker);
    svg.appendChild(defs);

    // Root Group transformed by Pan & Zoom
    const rootGroup = svgElement("g", {
        id: "graphViewport",
        transform: `translate(${graphView.x}, ${graphView.y}) scale(${graphView.scale})`
    });
    svg.appendChild(rootGroup);

    const n = simulation.processes;
    const m = simulation.resources;

    // Dynamic horizontal & vertical layout
    const svgWidth = 920;
    const svgHeight = 540;

    const processX = 180;
    const resourceX = 740;

    // Dynamic vertical spacing based on process and resource counts
    const processY = (i) => {
        if (n <= 1) return svgHeight / 2;
        const top = 65;
        const bottom = svgHeight - 65;
        return top + i * ((bottom - top) / (n - 1));
    };

    const resourceY = (j) => {
        if (m <= 1) return svgHeight / 2;
        const top = 100;
        const bottom = svgHeight - 100;
        return top + j * ((bottom - top) / (m - 1));
    };

    // Node dimension adaptation
    const pRadius = Math.max(22, Math.min(30, 260 / n));
    const rWidth = Math.max(76, Math.min(94, 700 / m));
    const rHeight = Math.max(44, Math.min(54, 450 / m));

    // 1. Draw Allocation Edges: Resource -> Process (Solid Blue)
    for (let i = 0; i < n; i++) {
        for (let j = 0; j < m; j++) {
            const quantity = simulation.allocation[i][j];
            if (quantity <= 0) continue;

            const x1 = resourceX - (rWidth / 2);
            const y1 = resourceY(j);
            const x2 = processX + pRadius;
            const y2 = processY(i);

            const midX = (x1 + x2) / 2;
            const midY = (y1 + y2) / 2;
            const curveOffsetY = (i - j) * 4;

            const path = svgElement("path", {
                d: `M ${x1} ${y1} Q ${midX} ${midY + curveOffsetY} ${x2} ${y2}`,
                class: "allocation-edge",
                "marker-end": "url(#allocationArrow)"
            });
            rootGroup.appendChild(path);

            addText(
                rootGroup,
                midX,
                midY + curveOffsetY - 8,
                quantity,
                "edge-label allocation-label"
            );
        }
    }

    // 2. Draw Temporary / Pending Request Edges: Process -> Resource (Dashed Orange)
    if (temporaryRequest) {
        const { process, values } = temporaryRequest;
        values.forEach((quantity, j) => {
            if (quantity <= 0) return;

            const x1 = processX + pRadius;
            const y1 = processY(process);
            const x2 = resourceX - (rWidth / 2);
            const y2 = resourceY(j);

            const midX = (x1 + x2) / 2;
            const midY = (y1 + y2) / 2;

            const path = svgElement("path", {
                d: `M ${x1} ${y1} L ${x2} ${y2}`,
                class: "request-edge",
                "marker-end": "url(#requestArrow)"
            });
            rootGroup.appendChild(path);

            addText(
                rootGroup,
                midX,
                midY + 18,
                quantity,
                "edge-label request-label"
            );
        });
    }

    // 3. Draw Process Nodes (Circles - Soft Blue)
    for (let i = 0; i < n; i++) {
        const group = svgElement("g", { class: "node-group" });
        const cy = processY(i);

        const circle = svgElement("circle", {
            cx: processX,
            cy: cy,
            r: pRadius,
            class: "process-node",
            id: `pnode-${i}`
        });
        group.appendChild(circle);

        const label = svgElement("text", {
            x: processX,
            y: cy + 5,
            class: "process-label",
            "text-anchor": "middle"
        });
        label.textContent = `P${i}`;
        group.appendChild(label);

        rootGroup.appendChild(group);
    }

    // 4. Draw Resource Nodes (Rounded Rectangles - Soft Violet)
    for (let j = 0; j < m; j++) {
        const y = resourceY(j);
        const group = svgElement("g", { class: "node-group" });

        const rect = svgElement("rect", {
            x: resourceX - (rWidth / 2),
            y: y - (rHeight / 2),
            width: rWidth,
            height: rHeight,
            rx: 10,
            class: "resource-node",
            id: `rnode-${j}`
        });
        group.appendChild(rect);

        const name = svgElement("text", {
            x: resourceX,
            y: y - 4,
            class: "resource-label",
            "text-anchor": "middle"
        });
        name.textContent = `R${j}`;
        group.appendChild(name);

        const count = svgElement("text", {
            x: resourceX,
            y: y + 14,
            class: "resource-count",
            "text-anchor": "middle",
            id: `rcount-${j}`
        });
        count.textContent = `${simulation.available[j]} avail`;
        group.appendChild(count);

        rootGroup.appendChild(group);
    }
}

// ==========================================================================
// Pan & Zoom Controls Setup
// ==========================================================================
function setupPanAndZoom() {
    const wrapper = $("canvasWrapper");

    function applyTransform() {
        const viewport = $("graphViewport");
        if (viewport) {
            viewport.setAttribute(
                "transform",
                `translate(${graphView.x}, ${graphView.y}) scale(${graphView.scale})`
            );
        }
    }

    // Wheel Zoom
    wrapper.addEventListener("wheel", (e) => {
        e.preventDefault();
        const factor = e.deltaY < 0 ? 1.1 : 0.9;
        const newScale = Math.min(Math.max(graphView.scale * factor, graphView.minScale), graphView.maxScale);

        const rect = wrapper.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;

        graphView.x = mouseX - (mouseX - graphView.x) * (newScale / graphView.scale);
        graphView.y = mouseY - (mouseY - graphView.y) * (newScale / graphView.scale);
        graphView.scale = newScale;

        applyTransform();
    }, { passive: false });

    // Drag to Pan
    wrapper.addEventListener("mousedown", (e) => {
        if (e.button !== 0) return;
        graphView.isPanning = true;
        graphView.startX = e.clientX - graphView.x;
        graphView.startY = e.clientY - graphView.y;
    });

    window.addEventListener("mousemove", (e) => {
        if (!graphView.isPanning) return;
        graphView.x = e.clientX - graphView.startX;
        graphView.y = e.clientY - graphView.startY;
        applyTransform();
    });

    window.addEventListener("mouseup", () => {
        graphView.isPanning = false;
    });

    // Toolbar Buttons
    $("zoomInBtn").addEventListener("click", () => {
        graphView.scale = Math.min(graphView.scale * 1.2, graphView.maxScale);
        applyTransform();
    });

    $("zoomOutBtn").addEventListener("click", () => {
        graphView.scale = Math.max(graphView.scale / 1.2, graphView.minScale);
        applyTransform();
    });

    $("resetViewBtn").addEventListener("click", () => {
        graphView.x = 0;
        graphView.y = 0;
        graphView.scale = 1;
        applyTransform();
    });

    $("fitScreenBtn").addEventListener("click", () => {
        graphView.x = 0;
        graphView.y = 0;
        graphView.scale = 1;
        applyTransform();
    });
}

// ==========================================================================
// Safe Sequence Animation Player (Section 5)
// ==========================================================================
function stopSafeAnimation() {
    if (animPlayer.timer) {
        clearInterval(animPlayer.timer);
        animPlayer.timer = null;
    }
    animPlayer.isPlaying = false;
    $("animPlayBtn").disabled = false;
    $("animPauseBtn").disabled = true;
    $("animRestartBtn").disabled = false;
}

function resetSafeAnimation() {
    stopSafeAnimation();
    animPlayer.stepIndex = 0;
    $("animProgressText").textContent = "Idle";

    // Clear all node highlights
    document.querySelectorAll(".process-node").forEach(node => {
        node.classList.remove("highlight-safe");
    });
    document.querySelectorAll(".resource-node").forEach(node => {
        node.classList.remove("highlight-active");
    });

    if (simulation) {
        $("availableValues").textContent = `[ ${simulation.available.join("  |  ")} ]`;
        for (let j = 0; j < simulation.resources; j++) {
            const countEl = $(`rcount-${j}`);
            if (countEl) countEl.textContent = `${simulation.available[j]} avail`;
        }
    }
}

async function startSafeAnimation() {
    if (!simulation) {
        log("Please initialize the simulation first.", "warn");
        return;
    }

    // Run actual safety check from C backend
    let safetyResult;
    try {
        safetyResult = await apiCall("/safety", "POST");
    } catch (e) {
        log(`Safety check error: ${e.message}`, "error");
        return;
    }

    if (!safetyResult.safe) {
        log("Cannot animate: System is in an UNSAFE state (Deadlock Risk).", "error");
        $("safetyStatus").textContent = "DEADLOCK RISK (UNSAFE)";
        $("safetyStatus").className = "status-badge-lg status-unsafe";
        $("safeSequence").textContent = "No safe sequence exists";
        return;
    }

    animPlayer.sequence = safetyResult.safe_sequence;
    animPlayer.workVector = [...simulation.available];
    animPlayer.stepIndex = 0;
    animPlayer.isPlaying = true;

    $("animPlayBtn").disabled = true;
    $("animPauseBtn").disabled = false;
    $("animRestartBtn").disabled = false;

    executeAnimationStep();
}

function executeAnimationStep() {
    if (!animPlayer.isPlaying) return;

    if (animPlayer.stepIndex >= animPlayer.sequence.length) {
        $("animProgressText").textContent = "Execution Complete! System is Safe.";
        log(`Animation completed: Entire safe sequence satisfied. Final Available Work: [ ${animPlayer.workVector.join(", ")} ]`, "success");
        stopSafeAnimation();
        return;
    }

    const currentProc = animPlayer.sequence[animPlayer.stepIndex];
    const pIdx = Number(currentProc.replace("P", ""));

    $("animProgressText").textContent = `Step ${animPlayer.stepIndex + 1}/${animPlayer.sequence.length}: Executing ${currentProc}`;
    log(`[Step ${animPlayer.stepIndex + 1}] Process ${currentProc} satisfies Need <= Work. Executing & releasing held resources...`, "info");

    // 1. Highlight Process Node
    const pNode = $(`pnode-${pIdx}`);
    if (pNode) pNode.classList.add("highlight-safe");

    // 2. Highlight Resource Nodes
    for (let j = 0; j < simulation.resources; j++) {
        const rNode = $(`rnode-${j}`);
        if (rNode) rNode.classList.add("highlight-active");
    }

    // 3. Return resources to Work vector
    for (let j = 0; j < simulation.resources; j++) {
        animPlayer.workVector[j] += simulation.allocation[pIdx][j];
    }

    // 4. Update displays
    $("availableValues").textContent = `[ ${animPlayer.workVector.join("  |  ")} ]`;
    for (let j = 0; j < simulation.resources; j++) {
        const countEl = $(`rcount-${j}`);
        if (countEl) countEl.textContent = `${animPlayer.workVector[j]} avail`;
    }

    // Step timer
    animPlayer.stepIndex++;
    animPlayer.timer = setTimeout(() => {
        document.querySelectorAll(".resource-node").forEach(node => node.classList.remove("highlight-active"));
        executeAnimationStep();
    }, 1200);
}

// ==========================================================================
// Initialization & Operations
// ==========================================================================
async function initializeSimulationFromInputs() {
    try {
        const payload = readConfigInputs();
        temporaryRequest = null;
        resetSafeAnimation();

        const result = await apiCall("/initialize", "POST", payload);

        updateDashboard(result.state);

        $("connectionStatus").textContent = "Core Online";
        $("connectionStatus").className = "status-badge status-online";

        $("safetyStatus").textContent = "Initialized (Ready)";
        $("safetyStatus").className = "status-badge-lg status-idle";
        $("safeSequence").textContent = "-";

        log(`Simulation initialized with ${payload.processes} processes and ${payload.resources} resources.`, "success");
    } catch (error) {
        showError(error);
    }
}

async function loadPreset(key) {
    const preset = PRESETS[key];
    if (!preset) return;

    // Update buttons
    document.querySelectorAll(".btn-chip").forEach(btn => btn.classList.remove("active"));
    const activeBtn = $(`preset${key}Btn`);
    if (activeBtn) activeBtn.classList.add("active");

    $("numProcessesInput").value = preset.processes;
    $("numResourcesInput").value = preset.resources;

    renderConfigInputs(preset.processes, preset.resources, preset);

    try {
        const result = await apiCall("/initialize", "POST", { preset: key });
        updateDashboard(result.state);
        resetSafeAnimation();

        $("connectionStatus").textContent = "Core Online";
        $("connectionStatus").className = "status-badge status-online";
        $("safetyStatus").textContent = "Initialized (Ready)";
        $("safetyStatus").className = "status-badge-lg status-idle";
        $("safeSequence").textContent = "-";

        log(`Preset ${key} (${preset.processes}P × ${preset.resources}R) loaded successfully.`, "info");
    } catch (e) {
        showError(e);
    }
}

// Run Safety Algorithm
async function runSafety() {
    try {
        const result = await apiCall("/safety", "POST");
        const statusEl = $("safetyStatus");

        if (result.safe) {
            statusEl.textContent = "SAFE STATE";
            statusEl.className = "status-badge-lg status-safe";
            $("safeSequence").textContent = result.safe_sequence.join(" → ");
            log(`Safety Check PASSED: System is in a SAFE state. Sequence: ${result.safe_sequence.join(" → ")}`, "success");
        } else {
            statusEl.textContent = "DEADLOCK RISK (UNSAFE)";
            statusEl.className = "status-badge-lg status-unsafe";
            $("safeSequence").textContent = "No safe execution sequence exists";
            log("Safety Check FAILED: System is in an UNSAFE state (Deadlock Risk)!", "error");
        }

        updateDashboard(result.state);
    } catch (error) {
        showError(error);
    }
}

// Submit Resource Request
async function submitRequest() {
    try {
        if (!simulation) throw new Error("Initialize simulation first.");

        const process = Number($("requestProcess").value);
        const values = [];
        for (let j = 0; j < simulation.resources; j++) {
            values.push(Number($(`reqVal_${j}`).value));
        }

        if (values.every(v => v === 0)) {
            throw new Error("Request vector cannot be all zeros.");
        }

        temporaryRequest = { process, values };
        renderGraph();

        const result = await apiCall("/request", "POST", { process, request: values });

        temporaryRequest = null;
        updateDashboard(result.state);
        resetSafeAnimation();

        const statusEl = $("safetyStatus");
        if (result.granted) {
            statusEl.textContent = "REQUEST GRANTED";
            statusEl.className = "status-badge-lg status-safe";
            log(result.message, "success");

            // Auto-refresh safety
            try {
                const safeCheck = await apiCall("/safety", "POST");
                $("safeSequence").textContent = safeCheck.safe
                    ? safeCheck.safe_sequence.join(" → ")
                    : "No safe sequence";
            } catch (e) { console.warn(e); }
        } else {
            statusEl.textContent = "REQUEST DENIED";
            statusEl.className = "status-badge-lg status-unsafe";
            log(result.message, "error");
        }

    } catch (error) {
        temporaryRequest = null;
        if (simulation) renderGraph();
        showError(error);
    }
}

// Release Resources
async function releaseResources() {
    try {
        if (!simulation) throw new Error("Initialize simulation first.");

        const process = Number($("releaseProcess").value);
        const values = [];
        for (let j = 0; j < simulation.resources; j++) {
            values.push(Number($(`relVal_${j}`).value));
        }

        if (values.every(v => v === 0)) {
            throw new Error("Release vector cannot be all zeros.");
        }

        const result = await apiCall("/release", "POST", { process, release: values });

        updateDashboard(result.state);
        resetSafeAnimation();

        if (result.released) {
            log(result.message, "success");
            try {
                const safeCheck = await apiCall("/safety", "POST");
                $("safeSequence").textContent = safeCheck.safe
                    ? safeCheck.safe_sequence.join(" → ")
                    : "No safe sequence";
            } catch (e) { console.warn(e); }
        } else {
            log(result.message, "error");
        }

    } catch (error) {
        showError(error);
    }
}

// Error Handler
function showError(error) {
    log(`Error: ${error.message}`, "error");
    console.error(error);
}

// ==========================================================================
// Event Bindings
// ==========================================================================
$("initializeBtn").addEventListener("click", initializeSimulationFromInputs);
$("applyDimensionsBtn").addEventListener("click", () => {
    const n = Math.max(1, Math.min(10, Number($("numProcessesInput").value)));
    const m = Math.max(1, Math.min(10, Number($("numResourcesInput").value)));
    $("numProcessesInput").value = n;
    $("numResourcesInput").value = m;
    renderConfigInputs(n, m);
    log(`Matrix input grid adjusted to ${n} Processes and ${m} Resources. Click "Initialize" to commit to C backend.`, "info");
});

$("preset3x2Btn").addEventListener("click", () => loadPreset("3x2"));
$("preset5x3Btn").addEventListener("click", () => loadPreset("5x3"));
$("preset6x4Btn").addEventListener("click", () => loadPreset("6x4"));

$("safetyBtn").addEventListener("click", runSafety);
$("requestBtn").addEventListener("click", submitRequest);
$("releaseBtn").addEventListener("click", releaseResources);

// Animation Controls
$("animPlayBtn").addEventListener("click", startSafeAnimation);
$("animPauseBtn").addEventListener("click", stopSafeAnimation);
$("animRestartBtn").addEventListener("click", () => {
    resetSafeAnimation();
    startSafeAnimation();
});
$("animResetBtn").addEventListener("click", resetSafeAnimation);

if ($("clearLogBtn")) {
    $("clearLogBtn").addEventListener("click", () => {
        $("executionLog").innerHTML = '<div class="log-line">Log cleared.</div>';
    });
}

// ==========================================================================
// Bootstrap
// ==========================================================================
async function initApp() {
    setupPanAndZoom();

    // Default configuration input setup
    renderConfigInputs(5, 3, PRESETS["5x3"]);

    try {
        const stateRes = await fetch(`${API}/state`);
        if (stateRes.ok) {
            const data = await stateRes.json();
            $("connectionStatus").textContent = "Core Online";
            $("connectionStatus").className = "status-badge status-online";
            updateDashboard(data);
            log("Connected to C Backend. Existing simulation state synchronized.", "info");
        } else {
            loadPreset("5x3");
        }
    } catch {
        $("connectionStatus").textContent = "Core Offline";
        $("connectionStatus").className = "status-badge status-offline";
        log("Backend offline. Please start server.py", "warn");
    }
}

initApp();
