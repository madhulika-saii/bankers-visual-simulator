import os
import sys
import ctypes
import subprocess
import streamlit as st
import pandas as pd
import numpy as np

# ==============================================================================
# STREAMLIT PAGE CONFIGURATION (PREMIUM LIGHT THEME)
# ==============================================================================
st.set_page_config(
    page_title="Banker's Algorithm & Resource Allocation Graph",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Light Theme CSS (SaaS Dashboard styling, navy text, soft blue & violet)
st.markdown("""
<style>
    /* Global Background and Fonts */
    .stApp {
        background-color: #F8FAFC !important;
        color: #1E293B !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    
    /* Top Header Bar */
    .header-box {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 20px;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
    }
    .header-title {
        font-size: 24px;
        font-weight: 700;
        color: #0F172A;
        margin: 0;
    }
    .header-subtitle {
        font-size: 14px;
        color: #64748B;
        margin-top: 4px;
    }

    /* Cards / Panels */
    .saas-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.04);
    }

    /* Graph Canvas Box */
    .graph-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 14px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        overflow: hidden;
    }

    /* Badge indicators */
    .badge-safe {
        background-color: #D1FAE5;
        color: #065F46;
        padding: 6px 14px;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 13px;
        display: inline-block;
        border: 1px solid #A7F3D0;
    }
    .badge-unsafe {
        background-color: #FFE4E6;
        color: #9F1239;
        padding: 6px 14px;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 13px;
        display: inline-block;
        border: 1px solid #FECDD3;
    }
    .badge-error {
        background-color: #FEE2E2;
        color: #B91C1C;
        padding: 8px 14px;
        border-radius: 8px;
        font-weight: 600;
        font-size: 13px;
        display: block;
        margin: 8px 0;
        border: 1px solid #FCA5A5;
    }
    .badge-info {
        background-color: #EFF6FF;
        color: #1E40AF;
        padding: 6px 14px;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 13px;
        display: inline-block;
        border: 1px solid #DBEAFE;
    }

    /* Algorithm Selection Badges */
    .badge-algo-rag {
        background-color: #FEF3C7;
        color: #92400E;
        padding: 6px 16px;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 13px;
        display: inline-block;
        border: 1px solid #FCD34D;
    }
    .badge-algo-bankers {
        background-color: #DBEAFE;
        color: #1E40AF;
        padding: 6px 16px;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 13px;
        display: inline-block;
        border: 1px solid #93C5FD;
    }
    .badge-algo-mixed {
        background-color: #EDE9FE;
        color: #5B21B6;
        padding: 6px 16px;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 13px;
        display: inline-block;
        border: 1px solid #C4B5FD;
    }
    .badge-cycle-deadlock {
        background-color: #FEE2E2;
        color: #991B1B;
        padding: 6px 14px;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 13px;
        display: inline-block;
        border: 1px solid #FCA5A5;
    }
    .badge-cycle-safe {
        background-color: #DCFCE7;
        color: #15803D;
        padding: 6px 14px;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 13px;
        display: inline-block;
        border: 1px solid #86EFAC;
    }

    /* Primary Buttons */
    div.stButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# BACKEND INTEGRATION: C SHARED LIBRARY VIA CTYPES
# ==============================================================================
MAX_P = 10
MAX_R = 10
Vector = ctypes.c_int * MAX_R
Matrix = (ctypes.c_int * MAX_R) * MAX_P
Sequence = ctypes.c_int * MAX_P
CyclePath = ctypes.c_int * (MAX_P * 2 + 2)

@st.cache_resource
def get_c_library():
    """Compiles and loads the C shared library for Banker's Algorithm and RAG Cycle Detection."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    src_file = os.path.join(base_dir, "backend", "bankers.c")

    if sys.platform == "win32":
        LIB_NAME = "bankers.dll"
    elif sys.platform == "darwin":
        LIB_NAME = "libbankers.dylib"
    else:
        LIB_NAME = "libbankers.so"

    lib_path = os.path.join(os.path.dirname(src_file), LIB_NAME)

    need_compile = not os.path.exists(lib_path)
    if not need_compile and os.path.getmtime(src_file) > os.path.getmtime(lib_path):
        need_compile = True

    if need_compile:
        try:
            gcc_cmd = ["gcc", "-Wall", "-Wextra", "-std=c11", "-O2", "-fPIC", "-shared", "-o", lib_path, src_file]
            subprocess.run(gcc_cmd, check=True, capture_output=True, text=True)
        except Exception as e:
            if not os.path.exists(lib_path):
                st.error(f"Failed to compile C shared library: {e}")
                st.stop()

    try:
        bankers = ctypes.CDLL(lib_path)
    except Exception as e:
        st.error(f"Failed to load C shared library ({lib_path}): {e}")
        st.stop()

    bankers.calculateNeed.argtypes = [
        ctypes.c_int, ctypes.c_int, Matrix, Matrix, Matrix
    ]
    bankers.calculateNeed.restype = ctypes.c_int

    bankers.safetyAlgorithm.argtypes = [
        ctypes.c_int, ctypes.c_int, Matrix, Matrix, Vector, Sequence
    ]
    bankers.safetyAlgorithm.restype = ctypes.c_int

    bankers.requestResources.argtypes = [
        ctypes.c_int, ctypes.c_int, ctypes.c_int, Vector, Matrix, Matrix, Vector
    ]
    bankers.requestResources.restype = ctypes.c_int

    bankers.releaseResources.argtypes = [
        ctypes.c_int, ctypes.c_int, Vector, Matrix, Matrix, Vector
    ]
    bankers.releaseResources.restype = ctypes.c_int

    bankers.detectRAGCycle.argtypes = [
        ctypes.c_int, ctypes.c_int, Matrix, Matrix, CyclePath, ctypes.POINTER(ctypes.c_int)
    ]
    bankers.detectRAGCycle.restype = ctypes.c_int

    return bankers, MAX_P, MAX_R, Vector, Matrix, Sequence

bankers_c, MAX_P, MAX_R, Vector, Matrix, Sequence = get_c_library()

# ==============================================================================
# BENCHMARK PRESETS (SUPPORTING ANY DYNAMIC DIMENSION & SINGLE/MULTI INSTANCE)
# ==============================================================================
PRESETS = {
    "Single-Instance: Deadlock Cycle (2 Processes × 2 Resources)": {
        "processes": 2,
        "resources": 2,
        "total": [1, 1],
        "allocation": [
            [1, 0],
            [0, 1]
        ],
        "maximum": [
            [1, 1],
            [1, 1]
        ]
    },
    "Single-Instance: Safe / No Cycle (3 Processes × 3 Resources)": {
        "processes": 3,
        "resources": 3,
        "total": [1, 1, 1],
        "allocation": [
            [1, 0, 0],
            [0, 1, 0],
            [0, 0, 0]
        ],
        "maximum": [
            [1, 1, 0],
            [0, 1, 1],
            [0, 0, 1]
        ]
    },
    "5 Processes × 3 Resources (Default)": {
        "processes": 5,
        "resources": 3,
        "total": [10, 5, 7],
        "allocation": [
            [0, 1, 0],
            [2, 0, 0],
            [3, 0, 2],
            [2, 1, 1],
            [0, 0, 2]
        ],
        "maximum": [
            [7, 5, 3],
            [3, 2, 2],
            [9, 0, 2],
            [2, 2, 2],
            [4, 3, 3]
        ]
    },
    "3 Processes × 2 Resources": {
        "processes": 3,
        "resources": 2,
        "total": [6, 6],
        "allocation": [
            [1, 2],
            [2, 1],
            [1, 2]
        ],
        "maximum": [
            [2, 3],
            [3, 2],
            [2, 4]
        ]
    },
    "6 Processes × 4 Resources": {
        "processes": 6,
        "resources": 4,
        "total": [12, 9, 10, 8],
        "allocation": [
            [1, 1, 1, 1],
            [2, 0, 1, 1],
            [3, 1, 2, 1],
            [1, 2, 1, 0],
            [1, 0, 1, 1],
            [1, 1, 1, 1]
        ],
        "maximum": [
            [3, 2, 2, 2],
            [4, 2, 3, 2],
            [5, 3, 4, 2],
            [3, 4, 2, 1],
            [2, 1, 2, 2],
            [3, 3, 2, 2]
        ]
    },
    "Mixed-Instance: 3 Processes × 3 Resources": {
        "processes": 3,
        "resources": 3,
        "total": [1, 4, 1],
        "allocation": [
            [1, 1, 0],
            [0, 1, 1],
            [0, 1, 0]
        ],
        "maximum": [
            [1, 2, 0],
            [0, 2, 1],
            [0, 2, 0]
        ]
    }
}

# ==============================================================================
# RIGOROUS VALIDATION HELPERS
# ==============================================================================
def validate_system_configuration(n, m, total, allocation, maximum):
    """
    Validates initial configuration:
    1. Dimensions match n and m.
    2. Non-negative allocation and maximum.
    3. Maximum >= Allocation for all i, j.
    4. Total[j] >= sum(Allocation[i][j]) for all j (preventing negative available).
    5. Single-instance capacity bounds (if Total[j] == 1, allocation cannot exceed 1).
    """
    errors = []

    if not (1 <= n <= MAX_P):
        errors.append(f"Process count must be between 1 and {MAX_P}.")
    if not (1 <= m <= MAX_R):
        errors.append(f"Resource type count must be between 1 and {MAX_R}.")

    if len(total) != m or len(allocation) != n or len(maximum) != n:
        errors.append("Dimension mismatch in configuration matrices.")
        return errors

    # Check Total non-negative
    for j in range(m):
        if total[j] < 0:
            errors.append(f"Total capacity for R{j} cannot be negative.")

    # Check Allocation <= Maximum and non-negativity
    for i in range(n):
        if len(allocation[i]) != m or len(maximum[i]) != m:
            errors.append(f"Process P{i} matrix row length mismatch.")
            continue
        for j in range(m):
            a = allocation[i][j]
            mx = maximum[i][j]
            if a < 0:
                errors.append(f"P{i}, R{j}: Allocation ({a}) cannot be negative.")
            if mx < 0:
                errors.append(f"P{i}, R{j}: Maximum ({mx}) cannot be negative.")
            if a > mx:
                errors.append(f"P{i}, R{j}: Allocation ({a}) exceeds Maximum declared demand ({mx}).")

    # Check Total >= Allocated (Available >= 0)
    for j in range(m):
        allocated_j = sum(allocation[i][j] for i in range(n))
        if allocated_j > total[j]:
            errors.append(
                f"Resource R{j}: Total allocated instances ({allocated_j}) exceed Total system capacity ({total[j]}). "
                f"Available would be negative ({total[j] - allocated_j})."
            )

    return errors

# ==============================================================================
# AUTOMATIC ALGORITHM SELECTION LOGIC
# ==============================================================================
def determine_algorithm_mode(total):
    """
    Determines algorithm selection based on resource instances:
    1. Case A (Single-Instance): All Total[j] == 1.
       -> Use Resource Allocation Graph (RAG) Cycle Detection.
       -> Cycle is NECESSARY and SUFFICIENT for deadlock.
    2. Case B (Multiple-Instance): All Total[j] > 1.
       -> Use Banker's Algorithm for Deadlock Avoidance.
       -> Cycle is NECESSARY but NOT SUFFICIENT. Banker's safety check required.
    3. Case C (Mixed-Instance): Some Total[j] == 1, others > 1.
       -> Use General Banker's Algorithm with RAG structural cycle analysis.
    """
    if all(t == 1 for t in total):
        return {
            "mode": "SINGLE_INSTANCE",
            "name": "Resource Allocation Graph (RAG) Cycle Detection",
            "badge_class": "badge-algo-rag",
            "reason": (
                "Every resource type has exactly 1 instance (Total = [1, ...]). "
                "Under the single-instance resource assumption, a directed cycle in the Resource "
                "Allocation Graph is a NECESSARY and SUFFICIENT condition for deadlock. "
                "Cycle detection is therefore the exact, definitive algorithm."
            ),
            "math_note": "Single-Instance Invariant: Graph Cycle ⟺ Deadlock (Necessary & Sufficient)."
        }
    elif all(t > 1 for t in total):
        return {
            "mode": "MULTI_INSTANCE",
            "name": "Banker's Algorithm (Deadlock Avoidance)",
            "badge_class": "badge-algo-bankers",
            "reason": (
                "Every resource type has multiple instances (Total > 1). "
                "In multiple-instance systems, a cycle in the RAG is only a NECESSARY condition, "
                "NOT a sufficient condition for deadlock (processes in a cycle can still proceed if other "
                "instances are available or released). Therefore, Dijkstra's Banker's Algorithm with "
                "Work and Finish vectors is required to evaluate safety."
            ),
            "math_note": "Multiple-Instance Invariant: Cycle is Necessary but NOT Sufficient. Safety check required."
        }
    else:
        single_types = [f"R{j}" for j, t in enumerate(total) if t == 1]
        multi_types = [f"R{j} ({t} inst)" for j, t in enumerate(total) if t > 1]
        return {
            "mode": "MIXED_INSTANCE",
            "name": "Banker's Algorithm (General Multi-Instance Mode)",
            "badge_class": "badge-algo-mixed",
            "reason": (
                f"Mixed-instance configuration detected: {', '.join(single_types)} are single-instance, "
                f"while {', '.join(multi_types)} are multi-instance. "
                "In Operating Systems theory, whenever any resource type has multiple instances, "
                "the simple single-instance cycle rule cannot be used as a sufficient condition for deadlock. "
                "Hence, the mathematically valid General Banker's Algorithm is applied for deadlock avoidance, "
                "alongside RAG cycle detection for structural graph insight."
            ),
            "math_note": "Mixed-Instance Invariant: General Banker's Algorithm guarantees safety across heterogeneous capacities."
        }

# ==============================================================================
# C CYCLE DETECTION HELPER
# ==============================================================================
def compute_rag_cycle(n, m, allocation, request_matrix):
    """
    Executes C detectRAGCycle to find directed cycles in the bipartite RAG.
    Returns:
        has_cycle (bool): True if directed cycle found.
        cycle_labels (list of str): Node path e.g. ['P0', 'R1', 'P1', 'R0', 'P0'].
        cycle_edges (set of tuples): Edge tuples e.g. {('P0', 'R1'), ('R1', 'P1'), ...}.
    """
    alloc_c = Matrix()
    req_c = Matrix()
    for i in range(n):
        for j in range(m):
            alloc_c[i][j] = int(allocation[i][j])
            req_c[i][j] = int(request_matrix[i][j])

    c_path = CyclePath()
    c_len = ctypes.c_int(0)
    has_cycle = bool(bankers_c.detectRAGCycle(n, m, alloc_c, req_c, c_path, ctypes.byref(c_len)))

    cycle_labels = []
    cycle_edges = set()
    if has_cycle and c_len.value > 0:
        raw_path = [c_path[k] for k in range(c_len.value)]
        for v in raw_path:
            if v < n:
                cycle_labels.append(f"P{v}")
            else:
                cycle_labels.append(f"R{v - n}")

        for k in range(len(cycle_labels) - 1):
            cycle_edges.add((cycle_labels[k], cycle_labels[k + 1]))

    return has_cycle, cycle_labels, cycle_edges

# ==============================================================================
# SESSION STATE INITIALIZATION
# ==============================================================================
if "initialized" not in st.session_state:
    preset = PRESETS["5 Processes × 3 Resources (Default)"]
    st.session_state.n = preset["processes"]
    st.session_state.m = preset["resources"]
    st.session_state.total = list(preset["total"])
    st.session_state.allocation = [list(r) for r in preset["allocation"]]
    st.session_state.maximum = [list(r) for r in preset["maximum"]]
    st.session_state.anim_index = 0
    st.session_state.pending_request = None
    st.session_state.request_status = None
    st.session_state.graph_zoom = 1.0
    st.session_state.graph_pan_x = 0
    st.session_state.graph_pan_y = 0
    st.session_state.initialized = True

if "pending_request" not in st.session_state:
    st.session_state.pending_request = None
if "request_status" not in st.session_state:
    st.session_state.request_status = None
if "graph_zoom" not in st.session_state:
    st.session_state.graph_zoom = 1.0
if "graph_pan_x" not in st.session_state:
    st.session_state.graph_pan_x = 0
if "graph_pan_y" not in st.session_state:
    st.session_state.graph_pan_y = 0

# ==============================================================================
# SIDEBAR CONFIGURATION (SECTION A: DYNAMIC PROCESS & RESOURCE SETUP)
# ==============================================================================
with st.sidebar:
    st.header("⚙️ System Configuration")
    st.markdown("Configure system dimensions, instance counts, or select standard benchmarks.")

    selected_preset = st.selectbox("Select Benchmark Preset", list(PRESETS.keys()), index=2)
    if st.button("Load Preset"):
        p_data = PRESETS[selected_preset]
        st.session_state.n = p_data["processes"]
        st.session_state.m = p_data["resources"]
        st.session_state.total = list(p_data["total"])
        st.session_state.allocation = [list(r) for r in p_data["allocation"]]
        st.session_state.maximum = [list(r) for r in p_data["maximum"]]
        st.session_state.anim_index = 0
        st.session_state.pending_request = None
        st.session_state.request_status = None
        st.session_state.graph_zoom = 1.0
        st.session_state.graph_pan_x = 0
        st.session_state.graph_pan_y = 0
        st.rerun()

    st.markdown("---")
    st.subheader("Resource Instance Mode")
    col_inst1, col_inst2 = st.columns(2)
    with col_inst1:
        if st.button("🔘 Single-Instance (1)", help="Set all resource total capacities to 1 instance"):
            st.session_state.total = [1] * st.session_state.m
            for i in range(st.session_state.n):
                for j in range(st.session_state.m):
                    st.session_state.allocation[i][j] = min(1, st.session_state.allocation[i][j])
                    st.session_state.maximum[i][j] = min(1, max(st.session_state.allocation[i][j], st.session_state.maximum[i][j]))
            st.session_state.pending_request = None
            st.session_state.request_status = None
            st.rerun()
    with col_inst2:
        if st.button("🔢 Multi-Instance (>1)", help="Set resource total capacities to multiple instances"):
            st.session_state.total = [max(5, st.session_state.total[j] * 3) for j in range(st.session_state.m)]
            st.session_state.pending_request = None
            st.session_state.request_status = None
            st.rerun()

    st.markdown("---")
    st.subheader("Custom Dimensions")
    new_n = st.slider("Processes (N)", min_value=1, max_value=MAX_P, value=st.session_state.n)
    new_m = st.slider("Resource Types (M)", min_value=1, max_value=MAX_R, value=st.session_state.m)

    if new_n != st.session_state.n or new_m != st.session_state.m:
        if st.button("Apply New Dimensions"):
            new_alloc = [[0]*new_m for _ in range(new_n)]
            new_max = [[2]*new_m for _ in range(new_n)]
            new_tot = [10]*new_m

            for i in range(min(new_n, st.session_state.n)):
                for j in range(min(new_m, st.session_state.m)):
                    new_alloc[i][j] = st.session_state.allocation[i][j]
                    new_max[i][j] = st.session_state.maximum[i][j]

            for j in range(min(new_m, st.session_state.m)):
                new_tot[j] = max(st.session_state.total[j], sum(new_alloc[i][j] for i in range(new_n)))

            st.session_state.n = new_n
            st.session_state.m = new_m
            st.session_state.total = new_tot
            st.session_state.allocation = new_alloc
            st.session_state.maximum = new_max
            st.session_state.anim_index = 0
            st.session_state.pending_request = None
            st.session_state.request_status = None
            st.session_state.graph_zoom = 1.0
            st.session_state.graph_pan_x = 0
            st.session_state.graph_pan_y = 0
            st.rerun()

    st.markdown("---")
    st.subheader("Total Capacity Vector (Total[j])")
    for j in range(st.session_state.m):
        allocated_j = sum(st.session_state.allocation[i][j] for i in range(st.session_state.n))
        st.session_state.total[j] = st.number_input(
            f"Total R{j} (Allocated: {allocated_j})",
            min_value=0,
            max_value=99,
            value=int(st.session_state.total[j]),
            key=f"tot_in_{j}"
        )

# ==============================================================================
# VALIDATION AND C-STATE COMPUTATION
# ==============================================================================
val_errors = validate_system_configuration(
    st.session_state.n,
    st.session_state.m,
    st.session_state.total,
    st.session_state.allocation,
    st.session_state.maximum
)

def compute_c_state():
    """Computes Need, Available, and Safety strictly via C implementation."""
    n = st.session_state.n
    m = st.session_state.m

    alloc_c = Matrix()
    max_c = Matrix()
    need_c = Matrix()
    avail_c = Vector()

    for i in range(n):
        for j in range(m):
            alloc_c[i][j] = int(st.session_state.allocation[i][j])
            max_c[i][j] = int(st.session_state.maximum[i][j])

    for j in range(m):
        allocated_j = sum(st.session_state.allocation[i][j] for i in range(n))
        avail_c[j] = int(st.session_state.total[j]) - allocated_j

    ok = bankers_c.calculateNeed(n, m, alloc_c, max_c, need_c)

    need = [[need_c[i][j] for j in range(m)] for i in range(n)]
    available = [avail_c[j] for j in range(m)]

    seq_c = Sequence()
    is_safe = False
    safe_seq = []
    if ok and all(a >= 0 for a in available):
        is_safe = bool(bankers_c.safetyAlgorithm(n, m, alloc_c, need_c, avail_c, seq_c))
        safe_seq = [f"P{seq_c[i]}" for i in range(n)] if is_safe else []

    return need, available, is_safe, safe_seq

if val_errors:
    for err in val_errors:
        st.markdown(f'<div class="badge-error">⚠️ {err}</div>', unsafe_allow_html=True)
    need_mat = [[max(0, st.session_state.maximum[i][j] - st.session_state.allocation[i][j]) for j in range(st.session_state.m)] for i in range(st.session_state.n)]
    avail_vec = [st.session_state.total[j] - sum(st.session_state.allocation[i][j] for i in range(st.session_state.n)) for j in range(st.session_state.m)]
    is_safe = False
    safe_seq = []
else:
    need_mat, avail_vec, is_safe, safe_seq = compute_c_state()

# Determine Algorithm Mode automatically
algo_info = determine_algorithm_mode(st.session_state.total)
mode = algo_info["mode"]

# Prepare effective request matrix for RAG cycle check
effective_request = [[0] * st.session_state.m for _ in range(st.session_state.n)]
for i in range(st.session_state.n):
    for j in range(st.session_state.m):
        effective_request[i][j] = need_mat[i][j]

if st.session_state.pending_request is not None:
    p_idx = st.session_state.pending_request.get("proc")
    p_vals = st.session_state.pending_request.get("values", [])
    if p_idx is not None and 0 <= p_idx < st.session_state.n:
        for j in range(min(st.session_state.m, len(p_vals))):
            effective_request[p_idx][j] = max(effective_request[p_idx][j], p_vals[j])

has_cycle, cycle_labels, cycle_edges = compute_rag_cycle(
    st.session_state.n, st.session_state.m, st.session_state.allocation, effective_request
)
cycle_nodes_set = set(cycle_labels) if has_cycle else set()

# ==============================================================================
# SVG RESOURCE ALLOCATION GRAPH GENERATOR (SOLID ALLOC, DOTTED REQUEST & CYCLE HIGHLIGHT)
# ==============================================================================
def generate_rag_svg(
    n, m, allocation, total, available, active_proc=None,
    pending_request=None, zoom=1.0, pan_x=0, pan_y=0,
    cycle_edges=None, cycle_nodes=None
):
    """
    Generates a large, clean, high-resolution SVG Resource Allocation Graph (RAG)
    supporting dynamic dimensions, pan & zoom, distinct solid allocation arrows,
    distinct dotted pending request arrows, and crimson cycle path highlighting.
    """
    width = 960
    height = max(560, max(n, m) * 75 + 130)

    px = 180
    rx = 760

    def py(i):
        if n <= 1: return (height - 60) / 2
        return 80 + i * ((height - 180) / (n - 1))

    def ry(j):
        if m <= 1: return (height - 60) / 2
        return 95 + j * ((height - 210) / (m - 1))

    p_rad = max(24, min(32, 280 / n))
    r_w = max(90, min(108, 750 / m))
    r_h = max(52, min(64, 480 / m))

    # Calculate ViewBox for Zoom and Pan
    z = max(0.4, min(3.0, float(zoom)))
    vb_w = width / z
    vb_h = height / z
    vb_x = ((width - vb_w) / 2) + pan_x
    vb_y = ((height - vb_h) / 2) + pan_y

    cycle_edges = cycle_edges or set()
    cycle_nodes = cycle_nodes or set()

    svg_parts = [
        f'<svg viewBox="{vb_x:.1f} {vb_y:.1f} {vb_w:.1f} {vb_h:.1f}" width="100%" height="{height}" xmlns="http://www.w3.org/2000/svg" style="background:#FFFFFF; border-radius:12px; display:block;">',
        '<defs>',
        '  <style>',
        '    @keyframes flowDashes { from { stroke-dashoffset: 24; } to { stroke-dashoffset: 0; } }',
        '    .rag-req-edge { stroke-dasharray: 7, 5; animation: flowDashes 1.2s linear infinite; }',
        '    .rag-cycle-edge { stroke-dasharray: none; }',
        '  </style>',
        '  <!-- Blue Arrowhead for Allocation: Resource -> Process -->',
        '  <marker id="allocArrow" markerWidth="10" markerHeight="10" refX="8" refY="3.5" orient="auto">',
        '    <path d="M0,0 L0,7 L8,3.5 z" fill="#2563EB"/>',
        '  </marker>',
        '  <!-- Orange Arrowhead for Request: Process -> Resource -->',
        '  <marker id="reqArrow" markerWidth="10" markerHeight="10" refX="8" refY="3.5" orient="auto">',
        '    <path d="M0,0 L0,7 L8,3.5 z" fill="#EA580C"/>',
        '  </marker>',
        '  <!-- Crimson Arrowhead for Cycle Edges -->',
        '  <marker id="cycleArrow" markerWidth="10" markerHeight="10" refX="8" refY="3.5" orient="auto">',
        '    <path d="M0,0 L0,7 L8,3.5 z" fill="#DC2626"/>',
        '  </marker>',
        '  <filter id="nodeShadow" x="-20%" y="-20%" width="140%" height="140%">',
        '    <feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="#0F172A" flood-opacity="0.08"/>',
        '  </filter>',
        '</defs>'
    ]

    # Parse Pending Request if active
    pending_proc = None
    pending_vals = [0] * m
    if pending_request and isinstance(pending_request, dict):
        p_idx = pending_request.get("proc")
        p_v = pending_request.get("values", [])
        if p_idx is not None and 0 <= p_idx < n:
            pending_proc = p_idx
            for j in range(min(m, len(p_v))):
                if p_v[j] > 0:
                    pending_vals[j] = p_v[j]

    # 1. Directed Allocation Edges (Resource -> Process)
    for i in range(n):
        for j in range(m):
            qty = allocation[i][j]
            if qty <= 0:
                continue

            x1 = rx - (r_w / 2)
            y1 = ry(j)
            x2 = px + p_rad
            y2 = py(i)

            mid_x = (x1 + x2) / 2
            mid_y = (y1 + y2) / 2

            # Check if this edge is in the detected cycle
            is_in_cycle = (f"R{j}", f"P{i}") in cycle_edges

            has_coexisting_req = (i == pending_proc and pending_vals[j] > 0)
            curve_y = ((i - j) * 6) + (18 if has_coexisting_req else 0)

            if is_in_cycle:
                stroke_color = "#DC2626"
                stroke_w = 3.5
                marker_id = "url(#cycleArrow)"
                label_color = "#DC2626"
            else:
                stroke_color = "#2563EB"
                stroke_w = 2.5
                marker_id = "url(#allocArrow)"
                label_color = "#1D4ED8"

            svg_parts.append(
                f'<path d="M {x1} {y1} Q {mid_x} {mid_y + curve_y} {x2} {y2}" stroke="{stroke_color}" stroke-width="{stroke_w}" fill="none" opacity="0.95" marker-end="{marker_id}"/>'
            )
            label_y = mid_y + curve_y + (16 if has_coexisting_req else -7)
            svg_parts.append(
                f'<text x="{mid_x}" y="{label_y}" font-family="Inter, sans-serif" font-size="12" font-weight="700" fill="{label_color}" text-anchor="middle" stroke="#FFFFFF" stroke-width="3" paint-order="stroke">{qty}</text>'
            )

    # 2. Directed Request Edges (Process -> Resource)
    # Render either active pending request or single-instance cycle/need requests
    for i in range(n):
        for j in range(m):
            req_qty = 0
            if pending_proc == i and pending_vals[j] > 0:
                req_qty = pending_vals[j]
            elif (f"P{i}", f"R{j}") in cycle_edges:
                req_qty = 1

            if req_qty <= 0:
                continue

            x1 = px + p_rad
            y1 = py(i)
            x2 = rx - (r_w / 2)
            y2 = ry(j)

            mid_x = (x1 + x2) / 2
            mid_y = (y1 + y2) / 2

            is_in_cycle = (f"P{i}", f"R{j}") in cycle_edges
            has_coexisting_alloc = (allocation[i][j] > 0)
            curve_y = ((i - j) * 6) - (20 if has_coexisting_alloc else 0)

            if is_in_cycle:
                stroke_color = "#DC2626"
                stroke_w = 3.5
                marker_id = "url(#cycleArrow)"
                label_color = "#DC2626"
                css_cls = "rag-cycle-edge"
            else:
                stroke_color = "#EA580C"
                stroke_w = 2.6
                marker_id = "url(#reqArrow)"
                label_color = "#EA580C"
                css_cls = "rag-req-edge"

            svg_parts.append(
                f'<path class="{css_cls}" d="M {x1} {y1} Q {mid_x} {mid_y + curve_y} {x2} {y2}" stroke="{stroke_color}" stroke-width="{stroke_w}" fill="none" opacity="0.95" marker-end="{marker_id}"/>'
            )
            label_y = mid_y + curve_y - (9 if has_coexisting_alloc else 7)
            svg_parts.append(
                f'<text x="{mid_x}" y="{label_y}" font-family="Inter, sans-serif" font-size="12" font-weight="700" fill="{label_color}" text-anchor="middle" stroke="#FFFFFF" stroke-width="3" paint-order="stroke">{req_qty} (req)</text>'
            )

    # 3. Process Nodes (Soft Blue / Crimson if in Deadlock Cycle)
    for i in range(n):
        cy = py(i)
        is_highlighted = active_proc == f"P{i}"
        has_pending = pending_proc == i
        is_in_cycle = f"P{i}" in cycle_nodes

        if is_in_cycle:
            fill_col = "#FEF2F2"
            stroke_col = "#DC2626"
            s_width = 3.5
            label_col = "#991B1B"
        elif is_highlighted:
            fill_col = "#ECFDF5"
            stroke_col = "#059669"
            s_width = 4
            label_col = "#059669"
        elif has_pending:
            fill_col = "#FFF7ED"
            stroke_col = "#EA580C"
            s_width = 3.2
            label_col = "#C2410C"
        else:
            fill_col = "#F0F9FF"
            stroke_col = "#0284C7"
            s_width = 2.5
            label_col = "#0369A1"

        svg_parts.append(
            f'<circle cx="{px}" cy="{cy}" r="{p_rad}" fill="{fill_col}" stroke="{stroke_col}" stroke-width="{s_width}" filter="url(#nodeShadow)"/>'
        )
        svg_parts.append(
            f'<text x="{px}" y="{cy + 5}" font-family="Inter, sans-serif" font-size="14" font-weight="700" fill="{label_col}" text-anchor="middle">{f"P{i}"}</text>'
        )

    # 4. Resource Nodes (Soft Violet / Crimson if in Deadlock Cycle)
    for j in range(m):
        y = ry(j)
        x_left = rx - (r_w / 2)
        y_top = y - (r_h / 2)
        avail = available[j]
        tot = total[j]
        alloc_tot = sum(allocation[i][j] for i in range(n))
        is_in_cycle = f"R{j}" in cycle_nodes

        if is_in_cycle:
            r_fill = "#FEF2F2"
            r_stroke = "#DC2626"
            r_swidth = 3.0
            r_txt = "#991B1B"
        else:
            r_fill = "#F5F3FF"
            r_stroke = "#7C3AED"
            r_swidth = 2.2
            r_txt = "#6D28D9"

        svg_parts.append(
            f'<rect x="{x_left}" y="{y_top}" width="{r_w}" height="{r_h}" rx="10" fill="{r_fill}" stroke="{r_stroke}" stroke-width="{r_swidth}" filter="url(#nodeShadow)"/>'
        )
        svg_parts.append(
            f'<text x="{rx}" y="{y - 10}" font-family="Inter, sans-serif" font-size="13" font-weight="700" fill="{r_txt}" text-anchor="middle">{f"R{j}"} (Total: {tot})</text>'
        )
        svg_parts.append(
            f'<text x="{rx}" y="{y + 6}" font-family="Inter, sans-serif" font-size="11" font-weight="600" fill="#2563EB" text-anchor="middle">Alloc: {alloc_tot}</text>'
        )
        avail_color = "#DC2626" if avail < 0 else ("#059669" if avail > 0 else "#64748B")
        svg_parts.append(
            f'<text x="{rx}" y="{y + 20}" font-family="Inter, sans-serif" font-size="11" font-weight="700" fill="{avail_color}" text-anchor="middle">Avail: {avail}</text>'
        )

    # 5. Integrated SVG Legend at Bottom
    leg_y = height - 44
    leg_w = 780 if not cycle_edges else 920
    svg_parts.append(
        f'<g transform="translate({(width / 2) - (leg_w / 2)}, {leg_y})">'
        f'<rect x="0" y="0" width="{leg_w}" height="34" rx="8" fill="#F8FAFC" stroke="#E2E8F0" stroke-width="1.2"/>'
        f'<line x1="20" y1="17" x2="60" y2="17" stroke="#2563EB" stroke-width="2.5" marker-end="url(#allocArrow)"/>'
        f'<text x="68" y="21" font-family="Inter, sans-serif" font-size="11" font-weight="600" fill="#1E293B">Allocation (Resource → Process)</text>'
        f'<line x1="270" y1="17" x2="310" y2="17" stroke="#EA580C" stroke-width="2.6" stroke-dasharray="6,4" marker-end="url(#reqArrow)"/>'
        f'<text x="318" y="21" font-family="Inter, sans-serif" font-size="11" font-weight="600" fill="#1E293B">Active Request (Process → Resource)</text>'
    )

    if cycle_edges:
        svg_parts.append(
            f'<line x1="535" y1="17" x2="570" y2="17" stroke="#DC2626" stroke-width="3" marker-end="url(#cycleArrow)"/>'
            f'<text x="576" y="21" font-family="Inter, sans-serif" font-size="11" font-weight="700" fill="#DC2626">Deadlock Cycle</text>'
            f'<circle cx="680" cy="17" r="6" fill="#F0F9FF" stroke="#0284C7" stroke-width="1.8"/>'
            f'<text x="692" y="21" font-family="Inter, sans-serif" font-size="11" font-weight="600" fill="#0369A1">Process</text>'
            f'<rect x="745" y="11" width="12" height="12" rx="3" fill="#F5F3FF" stroke="#7C3AED" stroke-width="1.8"/>'
            f'<text x="763" y="21" font-family="Inter, sans-serif" font-size="11" font-weight="600" fill="#6D28D9">Res</text>'
        )
    else:
        svg_parts.append(
            f'<circle cx="560" cy="17" r="6" fill="#F0F9FF" stroke="#0284C7" stroke-width="1.8"/>'
            f'<text x="572" y="21" font-family="Inter, sans-serif" font-size="11" font-weight="600" fill="#0369A1">Process</text>'
            f'<rect x="635" y="11" width="12" height="12" rx="3" fill="#F5F3FF" stroke="#7C3AED" stroke-width="1.8"/>'
            f'<text x="653" y="21" font-family="Inter, sans-serif" font-size="11" font-weight="600" fill="#6D28D9">Res</text>'
        )

    svg_parts.append('</g></svg>')
    return "".join(svg_parts)

# ==============================================================================
# TOP HEADER
# ==============================================================================
st.markdown("""
<div class="header-box">
    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
        <div>
            <h1 class="header-title">Banker's Algorithm & Resource Allocation Graph Simulator</h1>
            <p class="header-subtitle">Dual-Mode Operating Systems Engine: Automatic Algorithm Selection, C Core Safety & RAG Cycle Detection</p>
        </div>
        <div>
            <span class="badge-info">C Backend Engine (ctypes)</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ==============================================================================
# SECTION: AUTOMATIC ALGORITHM SELECTION
# ==============================================================================
inst_summary_items = [f"R{j}: {st.session_state.total[j]}" for j in range(st.session_state.m)]
inst_summary_str = " | ".join(inst_summary_items)

st.markdown(f"""
<div class="saas-card" style="border-left: 6px solid #2563EB; margin-bottom: 24px;">
    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; margin-bottom: 12px;">
        <div>
            <span style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; font-weight: 700; color: #64748B;">Algorithm Selection Engine</span>
            <h3 style="margin: 2px 0 0 0; font-size: 20px; font-weight: 700; color: #0F172A;">
                {algo_info['name']}
            </h3>
        </div>
        <div>
            <span class="{algo_info['badge_class']}">{algo_info['mode'].replace('_', ' ')}</span>
        </div>
    </div>
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; margin-bottom: 14px;">
        <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px;">
            <div style="font-size: 11px; font-weight: 700; color: #64748B; text-transform: uppercase;">Configured Resource Instances</div>
            <div style="font-size: 14px; font-weight: 600; color: #1E293B; margin-top: 4px;"><code>[ {inst_summary_str} ]</code></div>
        </div>
        <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px;">
            <div style="font-size: 11px; font-weight: 700; color: #64748B; text-transform: uppercase;">Theoretical Invariant</div>
            <div style="font-size: 13px; font-style: italic; color: #334155; margin-top: 4px;">{algo_info['math_note']}</div>
        </div>
    </div>
    <div style="font-size: 13.5px; color: #334155; line-height: 1.6;">
        <b>Selection Rationale:</b> {algo_info['reason']}
    </div>
</div>
""", unsafe_allow_html=True)

# ==============================================================================
# MAIN DASHBOARD PANELS
# ==============================================================================
col_main, col_ops = st.columns([2, 1], gap="large")

with col_main:
    # --------------------------------------------------------------------------
    # RESOURCE ALLOCATION GRAPH (HERO)
    # --------------------------------------------------------------------------
    st.subheader("📊 Resource Allocation Graph (RAG)")
    st.markdown(
        """
        <div style="display:flex; flex-wrap:wrap; gap:16px; margin-bottom:8px; font-size:12px; color:#475569;">
            <span>🔵 <b>Processes:</b> P0..P{n}</span>
            <span>🟣 <b>Resources:</b> R0..R{m}</span>
            <span><b style="color:#2563EB;">──► Allocation:</b> Solid Blue (Resource → Process)</span>
            <span><b style="color:#EA580C;">┄┄► Request:</b> Dotted Orange (Process → Resource)</span>
            {cycle_legend_span}
        </div>
        """.format(
            n=st.session_state.n - 1,
            m=st.session_state.m - 1,
            cycle_legend_span='<span><b style="color:#DC2626;">──► Deadlock Cycle:</b> Critical Path</span>' if has_cycle else ""
        ),
        unsafe_allow_html=True
    )

    # Graph Pan & Zoom Controls Toolbar
    z_c1, z_c2, z_c3, z_c4, z_c5, z_c6, z_c7 = st.columns([1, 1, 1, 1, 1, 1, 2])
    with z_c1:
        if st.button("➕ Zoom In", help="Zoom into the graph canvas"):
            st.session_state.graph_zoom = round(min(2.5, st.session_state.graph_zoom + 0.2), 2)
            st.rerun()
    with z_c2:
        if st.button("➖ Zoom Out", help="Zoom out of the graph canvas"):
            st.session_state.graph_zoom = round(max(0.6, st.session_state.graph_zoom - 0.2), 2)
            st.rerun()
    with z_c3:
        if st.button("⬅️ Left", help="Pan graph view left"):
            st.session_state.graph_pan_x -= 50
            st.rerun()
    with z_c4:
        if st.button("➡️ Right", help="Pan graph view right"):
            st.session_state.graph_pan_x += 50
            st.rerun()
    with z_c5:
        if st.button("⬆️ Up", help="Pan graph view up"):
            st.session_state.graph_pan_y -= 40
            st.rerun()
    with z_c6:
        if st.button("⬇️ Down", help="Pan graph view down"):
            st.session_state.graph_pan_y += 40
            st.rerun()
    with z_c7:
        zoom_pct = int(st.session_state.graph_zoom * 100)
        btn_label = f"🎯 Reset View ({zoom_pct}%)"
        if st.button(btn_label, help="Reset zoom and pan to fit screen"):
            st.session_state.graph_zoom = 1.0
            st.session_state.graph_pan_x = 0
            st.session_state.graph_pan_y = 0
            st.rerun()

    active_p = safe_seq[st.session_state.anim_index] if (safe_seq and st.session_state.anim_index < len(safe_seq)) else None
    svg_code = generate_rag_svg(
        n=st.session_state.n,
        m=st.session_state.m,
        allocation=st.session_state.allocation,
        total=st.session_state.total,
        available=avail_vec,
        active_proc=active_p,
        pending_request=st.session_state.pending_request,
        zoom=st.session_state.graph_zoom,
        pan_x=st.session_state.graph_pan_x,
        pan_y=st.session_state.graph_pan_y,
        cycle_edges=cycle_edges if mode == "SINGLE_INSTANCE" else None,
        cycle_nodes=cycle_nodes_set if mode == "SINGLE_INSTANCE" else None
    )
    st.markdown(f'<div class="graph-card">{svg_code}</div>', unsafe_allow_html=True)

    # --------------------------------------------------------------------------
    # VISUAL STEPPER / CYCLE DETAILS
    # --------------------------------------------------------------------------
    if mode == "SINGLE_INSTANCE":
        st.markdown("##### 🔍 Single-Instance Analysis Details")
        if has_cycle:
            st.error(f"🔴 **Cycle Path Detected:** {' → '.join(cycle_labels)}")
            st.markdown(
                "Under the single-instance resource model, this directed cycle proves that a "
                "circular wait exists among the processes involved. None of these processes can ever release "
                "their resources, producing permanent deadlock."
            )
        else:
            st.success("🟢 **Acyclic Graph Confirmed:** No directed cycles exist.")
            st.markdown(
                "Because every resource type has 1 instance and no cycle exists in the graph, "
                "the system is guaranteed to be deadlock-free."
            )
    else:
        st.markdown("##### 🎬 Safe Sequence Visual Stepper")
        anim_c1, anim_c2, anim_c3 = st.columns([1, 1, 2])
        with anim_c1:
            if st.button("▶️ Next Safe Step", disabled=(not is_safe or len(safe_seq) == 0)):
                if st.session_state.anim_index + 1 < len(safe_seq):
                    st.session_state.anim_index += 1
                else:
                    st.session_state.anim_index = 0
                st.rerun()
        with anim_c2:
            if st.button("🔄 Reset Animation"):
                st.session_state.anim_index = 0
                st.rerun()
        with anim_c3:
            if is_safe and safe_seq:
                curr_step = st.session_state.anim_index + 1
                st.info(f"Step {curr_step} of {len(safe_seq)}: Highlighted executing process **{safe_seq[st.session_state.anim_index]}**")
            else:
                st.warning("Animation disabled: No safe sequence exists for the current system state.")

with col_ops:
    # --------------------------------------------------------------------------
    # SYSTEM AUDIT & SAFETY STATUS
    # --------------------------------------------------------------------------
    st.subheader("🛡️ Safety & System Audit")

    if val_errors:
        st.markdown(f'<span class="badge-unsafe">CONFIGURATION ERROR</span>', unsafe_allow_html=True)
        st.error("System configuration is invalid. Please fix errors shown above.")
    elif mode == "SINGLE_INSTANCE":
        if has_cycle:
            st.markdown(f'<span class="badge-cycle-deadlock">❌ DEADLOCK DETECTED</span>', unsafe_allow_html=True)
            st.error(f"Cycle in RAG: {' → '.join(cycle_labels)}")
            st.markdown("**Cycle = Deadlock** (Single-Instance Rule)")
        else:
            st.markdown(f'<span class="badge-cycle-safe">✅ NO DEADLOCK</span>', unsafe_allow_html=True)
            st.success("Resource Allocation Graph is acyclic. System is safe.")
    else:
        if is_safe:
            st.markdown(f'<span class="badge-safe">SYSTEM IS SAFE</span>', unsafe_allow_html=True)
            st.success(f"Safe Sequence: {' → '.join(safe_seq)}")
        else:
            st.markdown(f'<span class="badge-unsafe">DEADLOCK RISK (UNSAFE)</span>', unsafe_allow_html=True)
            st.error("No safe execution sequence exists. Any further allocation risks deadlock.")

        if mode == "MIXED_INSTANCE":
            if has_cycle:
                st.warning(f"⚠️ Topological Cycle in RAG: {' → '.join(cycle_labels)} (Note: Cycle is necessary but not sufficient in mixed mode).")
            else:
                st.info("Topological RAG is acyclic.")

    st.markdown(f"**Available Resources Vector (Work):** `[ {' | '.join(str(x) for x in avail_vec)} ]`")
    st.markdown("---")

    # --------------------------------------------------------------------------
    # SUBMIT RESOURCE REQUEST
    # --------------------------------------------------------------------------
    st.subheader("📥 Submit Resource Request")
    proc_labels = [f"P{i}" for i in range(st.session_state.n)]
    req_proc = st.selectbox("Requesting Process", proc_labels, index=0)
    req_p_idx = int(req_proc[1:])

    # Display active pending request indicator banner if one exists
    if st.session_state.pending_request is not None:
        p_info = st.session_state.pending_request
        st.info(f"⏳ **Active Pending Request:** P{p_info['proc']} requesting `{p_info['values']}` (Dotted orange arrows visible on graph)")
        if st.button("❌ Clear Pending Request Arrow", key="btn_clear_pending"):
            st.session_state.pending_request = None
            st.session_state.request_status = None
            st.rerun()

    # Display previous request execution status message
    if st.session_state.request_status:
        stat = st.session_state.request_status
        if stat["type"] == "success":
            st.success(stat["msg"])
        elif stat["type"] == "error":
            st.error(stat["msg"])
        elif stat["type"] == "info":
            st.info(stat["msg"])

    req_cols = st.columns(st.session_state.m)
    req_vals = []
    for j in range(st.session_state.m):
        with req_cols[j]:
            val = st.number_input(f"Req R{j}", min_value=0, max_value=99, value=0, key=f"req_field_{j}")
            req_vals.append(val)

    b_col1, b_col2 = st.columns([1, 1])
    with b_col1:
        if st.button("👁️ Preview Request Arrow", help="Visualize dotted request arrows on the graph without committing", disabled=bool(val_errors)):
            if all(v == 0 for v in req_vals):
                st.warning("Please enter at least one non-zero request quantity to preview.")
            else:
                st.session_state.pending_request = {"proc": req_p_idx, "values": list(req_vals)}
                st.session_state.request_status = {
                    "type": "info",
                    "msg": f"Pending request for {req_proc} with values {req_vals} is now visible on the graph as dotted orange arrows."
                }
                st.rerun()

    with b_col2:
        if st.button("Submit Request to C Core", type="primary", disabled=bool(val_errors)):
            if all(v == 0 for v in req_vals):
                st.warning("Please enter at least one non-zero request quantity.")
            else:
                st.session_state.pending_request = {"proc": req_p_idx, "values": list(req_vals)}

                # Single-Instance specific validation: request cannot exceed 1
                if mode == "SINGLE_INSTANCE" and any(req_vals[j] > 1 for j in range(st.session_state.m)):
                    st.session_state.request_status = {
                        "type": "error",
                        "msg": "❌ Request Denied: In single-instance mode, request quantity cannot exceed 1."
                    }
                    st.rerun()

                # Check Need
                exceeds_need = any(req_vals[j] > need_mat[req_p_idx][j] for j in range(st.session_state.m))
                exceeds_avail = any(req_vals[j] > avail_vec[j] for j in range(st.session_state.m))

                if exceeds_need:
                    st.session_state.request_status = {
                        "type": "error",
                        "msg": f"❌ Request Denied for {req_proc}: Request {req_vals} exceeds maximum declared Need {need_mat[req_p_idx]}."
                    }
                    st.rerun()
                elif exceeds_avail:
                    st.session_state.request_status = {
                        "type": "error",
                        "msg": f"❌ Request Denied for {req_proc}: Insufficient Available resources in system (Requested: {req_vals}, Available: {avail_vec})."
                    }
                    st.rerun()
                else:
                    # In single-instance mode, check if granting the request creates a cycle
                    if mode == "SINGLE_INSTANCE":
                        # Tentative allocation test
                        tentative_alloc = [list(r) for r in st.session_state.allocation]
                        tentative_req = [list(r) for r in need_mat]
                        for j in range(st.session_state.m):
                            tentative_alloc[req_p_idx][j] += req_vals[j]
                            tentative_req[req_p_idx][j] = max(0, tentative_req[req_p_idx][j] - req_vals[j])

                        tent_cycle, tent_path, _ = compute_rag_cycle(
                            st.session_state.n, st.session_state.m, tentative_alloc, tentative_req
                        )
                        if tent_cycle:
                            st.session_state.request_status = {
                                "type": "error",
                                "msg": f"❌ Request Denied for {req_proc}: Allocation creates directed cycle ({' → '.join(tent_path)}), resulting in deadlock! Rolled back."
                            }
                            st.rerun()
                        else:
                            for j in range(st.session_state.m):
                                st.session_state.allocation[req_p_idx][j] += req_vals[j]
                            st.session_state.pending_request = None
                            st.session_state.request_status = {
                                "type": "success",
                                "msg": f"✅ Request Granted to {req_proc}! Single-instance RAG remains acyclic and safe."
                            }
                            st.rerun()
                    else:
                        # Multi-instance / Mixed: Call C backend requestResources with safety check and rollback
                        alloc_c = Matrix()
                        max_c = Matrix()
                        need_c = Matrix()
                        avail_c = Vector()
                        req_c = Vector()

                        for i in range(st.session_state.n):
                            for j in range(st.session_state.m):
                                alloc_c[i][j] = int(st.session_state.allocation[i][j])
                                max_c[i][j] = int(st.session_state.maximum[i][j])
                                need_c[i][j] = int(need_mat[i][j])

                        for j in range(st.session_state.m):
                            avail_c[j] = int(avail_vec[j])
                            req_c[j] = int(req_vals[j])

                        granted = bankers_c.requestResources(
                            req_p_idx, st.session_state.n, st.session_state.m, req_c, alloc_c, need_c, avail_c
                        )

                        if granted:
                            for j in range(st.session_state.m):
                                st.session_state.allocation[req_p_idx][j] += req_vals[j]
                            st.session_state.pending_request = None
                            st.session_state.request_status = {
                                "type": "success",
                                "msg": f"✅ Request Granted to {req_proc} by C Core! Allocation state updated, pending request edge removed."
                            }
                            st.rerun()
                        else:
                            st.session_state.request_status = {
                                "type": "error",
                                "msg": f"❌ Request Denied for {req_proc}: Allocation leads to an unsafe state (Deadlock Risk). C algorithm rolled back."
                            }
                            st.rerun()

    st.markdown("---")

    # --------------------------------------------------------------------------
    # RELEASE RESOURCES
    # --------------------------------------------------------------------------
    st.subheader("📤 Release Resources")
    rel_proc = st.selectbox("Releasing Process", proc_labels, index=0, key="rel_p_sel")
    rel_p_idx = int(rel_proc[1:])

    rel_cols = st.columns(st.session_state.m)
    rel_vals = []
    for j in range(st.session_state.m):
        with rel_cols[j]:
            val = st.number_input(f"Rel R{j}", min_value=0, max_value=99, value=0, key=f"rel_field_{j}")
            rel_vals.append(val)

    if st.button("Release Resources in C Core", disabled=bool(val_errors)):
        if all(v == 0 for v in rel_vals):
            st.warning("Please enter at least one non-zero release quantity.")
        elif any(rel_vals[j] > st.session_state.allocation[rel_p_idx][j] for j in range(st.session_state.m)):
            st.error("❌ Release Denied: Process cannot release more than its currently held allocation.")
        else:
            for j in range(st.session_state.m):
                st.session_state.allocation[rel_p_idx][j] -= rel_vals[j]
            st.session_state.pending_request = None
            st.session_state.request_status = {
                "type": "success",
                "msg": f"✅ Resources successfully released by {rel_proc}!"
            }
            st.rerun()

# ==============================================================================
# SECTION D, E, F: MATRICES
# ==============================================================================
st.markdown("---")
st.subheader("📋 System Resource Matrices")

mat_col1, mat_col2, mat_col3 = st.columns(3)

r_labels = [f"R{j}" for j in range(st.session_state.m)]
p_indices = [f"P{i}" for i in range(st.session_state.n)]

with mat_col1:
    st.markdown("##### Allocation Matrix (Currently Held)")
    df_alloc = pd.DataFrame(st.session_state.allocation, index=p_indices, columns=r_labels)
    st.dataframe(df_alloc, use_container_width=True)

with mat_col2:
    st.markdown("##### Maximum Claim Matrix")
    df_max = pd.DataFrame(st.session_state.maximum, index=p_indices, columns=r_labels)
    st.dataframe(df_max, use_container_width=True)

with mat_col3:
    st.markdown("##### Need / Request Matrix (Max - Allocation)")
    df_need = pd.DataFrame(need_mat, index=p_indices, columns=r_labels)
    st.dataframe(df_need, use_container_width=True)

st.markdown("""
<div style="text-align: center; color: #94A3B8; font-size: 12px; margin-top: 40px; border-top: 1px solid #E2E8F0; padding-top: 16px;">
    Operating Systems Project • Dual-Mode Banker's Algorithm & RAG Cycle Detector • SaaS Edition
</div>
""", unsafe_allow_html=True)
