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
        margin-bottom: 24px;
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
        padding: 16px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
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

    /* Primary Buttons */
    div.stButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# C LIBRARY AUTO-COMPILATION & CTYPES BINDING
# ==============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IS_WINDOWS = sys.platform == "win32"
LIB_NAME = "libbankers.dll" if IS_WINDOWS else "libbankers.so"

def get_c_library():
    """Locates or automatically compiles bankers.c into a shared library."""
    c_src_candidates = [
        os.path.join(BASE_DIR, "backend", "bankers.c"),
        os.path.join(BASE_DIR, "bankers.c")
    ]
    src_file = next((p for p in c_src_candidates if os.path.exists(p)), None)
    if not src_file:
        st.error(f"Cannot find 'bankers.c'. Searched: {c_src_candidates}")
        st.stop()

    lib_path = os.path.join(os.path.dirname(src_file), LIB_NAME)

    # Compile with GCC on Linux / Streamlit Cloud or Windows GCC if library missing
    need_compile = not os.path.exists(lib_path)
    if not need_compile and os.path.getmtime(src_file) > os.path.getmtime(lib_path):
        need_compile = True

    if need_compile:
        try:
            gcc_cmd = ["gcc", "-Wall", "-Wextra", "-std=c11", "-O2", "-fPIC", "-shared", "-o", lib_path, src_file]
            subprocess.run(gcc_cmd, check=True, capture_output=True, text=True)
        except Exception as e:
            # Fallback check if existing binary exists in repo
            if not os.path.exists(lib_path):
                st.error(f"Failed to compile C shared library: {e}")
                st.stop()

    try:
        cdll = ctypes.CDLL(lib_path)
    except Exception as e:
        st.error(f"Failed to load C shared library ({lib_path}): {e}")
        st.stop()

    # Configure ctypes types and signatures
    MAX_P = 10
    MAX_R = 10
    Vector = ctypes.c_int * MAX_R
    Matrix = (ctypes.c_int * MAX_R) * MAX_P
    Sequence = ctypes.c_int * MAX_P

    cdll.calculateNeed.argtypes = [ctypes.c_int, ctypes.c_int, Matrix, Matrix, Matrix]
    cdll.calculateNeed.restype = ctypes.c_int

    cdll.safetyAlgorithm.argtypes = [ctypes.c_int, ctypes.c_int, Matrix, Matrix, Vector, Sequence]
    cdll.safetyAlgorithm.restype = ctypes.c_int

    cdll.requestResources.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, Vector, Matrix, Matrix, Vector]
    cdll.requestResources.restype = ctypes.c_int

    cdll.releaseResources.argtypes = [ctypes.c_int, ctypes.c_int, Vector, Matrix, Matrix, Vector]
    cdll.releaseResources.restype = ctypes.c_int

    return cdll, MAX_P, MAX_R, Vector, Matrix, Sequence

bankers_c, MAX_P, MAX_R, Vector, Matrix, Sequence = get_c_library()

# ==============================================================================
# BUILT-IN BENCHMARKS / PRESETS
# ==============================================================================
PRESETS = {
    "3 Processes × 2 Resources": {
        "processes": 3,
        "resources": 2,
        "total": [5, 5],
        "allocation": [[1, 1], [2, 1], [1, 2]],
        "maximum": [[2, 2], [2, 2], [3, 3]]
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
    "6 Processes × 4 Resources": {
        "processes": 6,
        "resources": 4,
        "total": [12, 9, 10, 8],
        "allocation": [
            [1, 1, 0, 1],
            [2, 0, 1, 1],
            [3, 1, 2, 1],
            [1, 2, 1, 0],
            [1, 0, 1, 1],
            [1, 1, 1, 1]
        ],
        "maximum": [
            [3, 2, 1, 2],
            [4, 1, 2, 2],
            [4, 2, 3, 2],
            [2, 3, 2, 1],
            [3, 2, 2, 2],
            [2, 2, 2, 2]
        ]
    }
}

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
    st.session_state.initialized = True

def compute_c_state():
    """Computes Need and Available vectors using actual C implementation."""
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
        used = sum(st.session_state.allocation[i][j] for i in range(n))
        avail_c[j] = int(st.session_state.total[j]) - used

    # Compute Need in C
    ok = bankers_c.calculateNeed(n, m, alloc_c, max_c, need_c)

    need = [[need_c[i][j] for j in range(m)] for i in range(n)]
    available = [avail_c[j] for j in range(m)]

    # Compute Safety in C
    seq_c = Sequence()
    is_safe = bool(bankers_c.safetyAlgorithm(n, m, alloc_c, need_c, avail_c, seq_c))
    safe_seq = [f"P{seq_c[i]}" for i in range(n)] if is_safe else []

    return need, available, is_safe, safe_seq

# ==============================================================================
# SVG RESOURCE ALLOCATION GRAPH GENERATOR
# ==============================================================================
def generate_rag_svg(n, m, allocation, available, active_proc=None):
    """Generates a large, clean, high-resolution SVG Resource Allocation Graph."""
    width = 920
    height = max(520, max(n, m) * 65 + 100)

    px = 180
    rx = 740

    def py(i):
        if n <= 1: return height / 2
        return 70 + i * ((height - 140) / (n - 1))

    def ry(j):
        if m <= 1: return height / 2
        return 100 + j * ((height - 200) / (m - 1))

    p_rad = max(24, min(32, 280 / n))
    r_w = max(80, min(96, 750 / m))
    r_h = max(46, min(56, 480 / m))

    svg_parts = [
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" xmlns="http://www.w3.org/2000/svg" style="background:#FFFFFF; border-radius:12px;">',
        '<defs>',
        '  <marker id="allocArrow" markerWidth="9" markerHeight="9" refX="7" refY="3.5" orient="auto">',
        '    <path d="M0,0 L0,7 L7,3.5 z" fill="#2563EB"/>',
        '  </marker>',
        '  <filter id="nodeShadow" x="-20%" y="-20%" width="140%" height="140%">',
        '    <feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="#0F172A" flood-opacity="0.08"/>',
        '  </filter>',
        '</defs>'
    ]

    # Directed Allocation Edges (Resource -> Process, Solid Blue)
    for i in range(n):
        for j in range(m):
            qty = allocation[i][j]
            if qty <= 0: continue

            x1 = rx - (r_w / 2)
            y1 = ry(j)
            x2 = px + p_rad
            y2 = py(i)

            mid_x = (x1 + x2) / 2
            mid_y = (y1 + y2) / 2
            curve_y = (i - j) * 5

            svg_parts.append(
                f'<path d="M {x1} {y1} Q {mid_x} {mid_y + curve_y} {x2} {y2}" stroke="#2563EB" stroke-width="2.5" fill="none" opacity="0.9" marker-end="url(#allocArrow)"/>'
            )
            svg_parts.append(
                f'<text x="{mid_x}" y="{mid_y + curve_y - 7}" font-family="Inter, sans-serif" font-size="12" font-weight="700" fill="#1D4ED8" text-anchor="middle" stroke="#FFFFFF" stroke-width="3" paint-order="stroke">{qty}</text>'
            )

    # Process Nodes (Soft Blue)
    for i in range(n):
        cy = py(i)
        is_highlighted = active_proc == f"P{i}"
        fill_col = "#ECFDF5" if is_highlighted else "#F0F9FF"
        stroke_col = "#059669" if is_highlighted else "#0284C7"
        s_width = 4 if is_highlighted else 2.5

        svg_parts.append(
            f'<circle cx="{px}" cy="{cy}" r="{p_rad}" fill="{fill_col}" stroke="{stroke_col}" stroke-width="{s_width}" filter="url(#nodeShadow)"/>'
        )
        svg_parts.append(
            f'<text x="{px}" y="{cy + 5}" font-family="Inter, sans-serif" font-size="14" font-weight="700" fill="#0369A1" text-anchor="middle">{f"P{i}"}</text>'
        )

    # Resource Nodes (Soft Violet)
    for j in range(m):
        y = ry(j)
        x_left = rx - (r_w / 2)
        y_top = y - (r_h / 2)
        avail = available[j]

        svg_parts.append(
            f'<rect x="{x_left}" y="{y_top}" width="{r_w}" height="{r_h}" rx="10" fill="#F5F3FF" stroke="#7C3AED" stroke-width="2.2" filter="url(#nodeShadow)"/>'
        )
        svg_parts.append(
            f'<text x="{rx}" y="{y - 4}" font-family="Inter, sans-serif" font-size="13" font-weight="700" fill="#6D28D9" text-anchor="middle">{f"R{j}"}</text>'
        )
        svg_parts.append(
            f'<text x="{rx}" y="{y + 14}" font-family="Inter, sans-serif" font-size="11" font-weight="600" fill="#7C3AED" text-anchor="middle">{avail} avail</text>'
        )

    svg_parts.append('</svg>')
    return "".join(svg_parts)

# ==============================================================================
# HEADER
# ==============================================================================
st.markdown("""
<div class="header-box">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <h1 class="header-title">Banker's Algorithm Simulator</h1>
            <p class="header-subtitle">Interactive Deadlock Avoidance, Real-Time C Core Execution & Resource Allocation Graph</p>
        </div>
        <div>
            <span class="badge-info">C Backend Engine (ctypes)</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Compute live state
need_mat, avail_vec, is_safe, safe_seq = compute_c_state()

# ==============================================================================
# SIDEBAR CONFIGURATION (SECTION A: DYNAMIC PROCESS & RESOURCE SETUP)
# ==============================================================================
with st.sidebar:
    st.header("⚙️ System Configuration")
    st.markdown("Configure system dimensions or select standard benchmarks.")

    selected_preset = st.selectbox("Select Benchmark Preset", list(PRESETS.keys()), index=1)
    if st.button("Load Preset"):
        p_data = PRESETS[selected_preset]
        st.session_state.n = p_data["processes"]
        st.session_state.m = p_data["resources"]
        st.session_state.total = list(p_data["total"])
        st.session_state.allocation = [list(r) for r in p_data["allocation"]]
        st.session_state.maximum = [list(r) for r in p_data["maximum"]]
        st.session_state.anim_index = 0
        st.rerun()

    st.markdown("---")
    st.subheader("Custom Dimensions")
    new_n = st.slider("Processes (N)", min_value=1, max_value=MAX_P, value=st.session_state.n)
    new_m = st.slider("Resource Types (M)", min_value=1, max_value=MAX_R, value=st.session_state.m)

    if new_n != st.session_state.n or new_m != st.session_state.m:
        if st.button("Apply New Dimensions"):
            # Resize matrices preserving existing data
            new_alloc = [[0]*new_m for _ in range(new_n)]
            new_max = [[2]*new_m for _ in range(new_n)]
            new_tot = [10]*new_m

            for i in range(min(new_n, st.session_state.n)):
                for j in range(min(new_m, st.session_state.m)):
                    new_alloc[i][j] = st.session_state.allocation[i][j]
                    new_max[i][j] = st.session_state.maximum[i][j]

            for j in range(min(new_m, st.session_state.m)):
                new_tot[j] = st.session_state.total[j]

            st.session_state.n = new_n
            st.session_state.m = new_m
            st.session_state.total = new_tot
            st.session_state.allocation = new_alloc
            st.session_state.maximum = new_max
            st.session_state.anim_index = 0
            st.rerun()

    st.markdown("---")
    st.subheader("Total Instances Vector")
    for j in range(st.session_state.m):
        st.session_state.total[j] = st.number_input(
            f"Total R{j}", min_value=0, max_value=99, value=int(st.session_state.total[j]), key=f"tot_in_{j}"
        )

# ==============================================================================
# MAIN DASHBOARD TABS & PANELS
# ==============================================================================
col_main, col_ops = st.columns([2, 1], gap="large")

with col_main:
    # --------------------------------------------------------------------------
    # SECTION B: RESOURCE ALLOCATION GRAPH (HERO)
    # --------------------------------------------------------------------------
    st.subheader("📊 Resource Allocation Graph (RAG)")
    st.markdown(
        """
        <div style="display:flex; gap:16px; margin-bottom:8px; font-size:12px; color:#475569;">
            <span>🔵 <b>Processes:</b> P0..P{n}</span>
            <span>🟣 <b>Resources:</b> R0..R{m}</span>
            <span><b style="color:#2563EB;">→ Allocation:</b> Resource to Process</span>
            <span><b style="color:#EA580C;">⇢ Request:</b> Process to Resource</span>
        </div>
        """.format(n=st.session_state.n-1, m=st.session_state.m-1),
        unsafe_allow_html=True
    )

    active_p = safe_seq[st.session_state.anim_index] if (safe_seq and st.session_state.anim_index < len(safe_seq)) else None
    svg_code = generate_rag_svg(st.session_state.n, st.session_state.m, st.session_state.allocation, avail_vec, active_p)
    st.markdown(f'<div class="graph-card">{svg_code}</div>', unsafe_allow_html=True)

    # --------------------------------------------------------------------------
    # SAFE SEQUENCE ANIMATION CONTROLS
    # --------------------------------------------------------------------------
    st.markdown("##### 🎬 Safe Sequence Visual Stepper")
    anim_c1, anim_c2, anim_c3 = st.columns([1, 1, 2])
    with anim_c1:
        if st.button("▶️ Next Safe Step", disabled=not is_safe):
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

with col_ops:
    # --------------------------------------------------------------------------
    # SECTION I & J: SAFETY CHECK & AUDIT STATUS
    # --------------------------------------------------------------------------
    st.subheader("🛡️ Safety & System Audit")
    if is_safe:
        st.markdown(f'<span class="badge-safe">SYSTEM IS SAFE</span>', unsafe_allow_html=True)
        st.success(f"Safe Sequence: {' → '.join(safe_seq)}")
    else:
        st.markdown(f'<span class="badge-unsafe">DEADLOCK RISK (UNSAFE)</span>', unsafe_allow_html=True)
        st.error("No safe execution sequence exists. Any further allocation risks deadlock.")

    st.markdown(f"**Available Resources Vector (Work):** `[ {' | '.join(str(x) for x in avail_vec)} ]`")
    st.markdown("---")

    # --------------------------------------------------------------------------
    # SECTION G: RESOURCE REQUEST OPERATION
    # --------------------------------------------------------------------------
    st.subheader("📥 Submit Resource Request")
    proc_labels = [f"P{i}" for i in range(st.session_state.n)]
    req_proc = st.selectbox("Requesting Process", proc_labels, index=0)
    req_p_idx = int(req_proc[1:])

    req_cols = st.columns(st.session_state.m)
    req_vals = []
    for j in range(st.session_state.m):
        with req_cols[j]:
            val = st.number_input(f"Req R{j}", min_value=0, max_value=99, value=0, key=f"req_field_{j}")
            req_vals.append(val)

    if st.button("Submit Request to C Core", type="primary"):
        if all(v == 0 for v in req_vals):
            st.warning("Please enter at least one non-zero request quantity.")
        else:
            # Check Need
            exceeds_need = any(req_vals[j] > need_mat[req_p_idx][j] for j in range(st.session_state.m))
            exceeds_avail = any(req_vals[j] > avail_vec[j] for j in range(st.session_state.m))

            if exceeds_need:
                st.error("❌ Request Denied: Exceeds process's maximum declared Need.")
            elif exceeds_avail:
                st.error("❌ Request Denied: Insufficient Available resources in the system.")
            else:
                # Call C backend requestResources
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
                    st.success(f"✅ Request Granted to {req_proc} by C Core! Allocation state updated.")
                    st.rerun()
                else:
                    st.error(f"❌ Request Denied for {req_proc}: Allocation leads to an unsafe state. C algorithm rolled back.")

    st.markdown("---")

    # --------------------------------------------------------------------------
    # SECTION H: RESOURCE RELEASE OPERATION
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

    if st.button("Release Resources in C Core"):
        if all(v == 0 for v in rel_vals):
            st.warning("Please enter at least one non-zero release quantity.")
        elif any(rel_vals[j] > st.session_state.allocation[rel_p_idx][j] for j in range(st.session_state.m)):
            st.error("❌ Release Denied: Process cannot release more than its currently held allocation.")
        else:
            for j in range(st.session_state.m):
                st.session_state.allocation[rel_p_idx][j] -= rel_vals[j]
            st.success(f"✅ Resources successfully released by {rel_proc}!")
            st.rerun()

# ==============================================================================
# SECTION D, E, F: MATRICES
# ==============================================================================
st.markdown("---")
st.subheader("📋 System Resource Matrices (Calculated via C Core)")

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
    st.markdown("##### Need Matrix (Max - Allocation)")
    df_need = pd.DataFrame(need_mat, index=p_indices, columns=r_labels)
    st.dataframe(df_need, use_container_width=True)

st.markdown("""
<div style="text-align: center; color: #94A3B8; font-size: 12px; margin-top: 40px; border-top: 1px solid #E2E8F0; padding-top: 16px;">
    Operating Systems Project • Banker's Algorithm Simulation • Light Theme SaaS Edition
</div>
""", unsafe_allow_html=True)
