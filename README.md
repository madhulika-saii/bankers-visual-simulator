# Graph-Based Banker's Algorithm Simulator

An interactive Operating Systems simulator for deadlock avoidance using Dijkstra's Banker's Algorithm and bipartite Resource Allocation Graphs (RAG).

## Features
- **Dynamic System Dimensions**: Configure between 1 to 10 processes ($P_0 \dots P_{N-1}$) and 1 to 10 resource types ($R_0 \dots R_{M-1}$).
- **Built-in Presets**: Quick loading for $3 \times 2$, $5 \times 3$ (standard benchmark), and $6 \times 4$.
- **High-Resolution Resource Allocation Graph (RAG)**:
  - Directed Allocation edges: Resource $\to$ Process ($R_j \to P_i$, solid blue).
  - Directed Request edges: Process $\to$ Resource ($P_i \to R_j$, dashed orange).
  - Interactive pan, zoom, fit-to-screen, and reset controls.
- **Real-Time State Matrices**: Live Allocation, Maximum Claim, Need ($\text{Need} = \text{Maximum} - \text{Allocation}$), and Available vectors computed directly in C.
- **Interactive Operations**:
  - Request resources with automatic safety check and state rollback on deadlock risk.
  - Release resources with bounds verification.
- **Safe Sequence Visual Animation**: Step-by-step process execution with real-time Work vector recovery.
- **Pure C Core Implementation**: The algorithm logic is written in C (`bankers.c`), compiled to a shared library (`libbankers.so`), and bound via Python `ctypes`.
- **Modern Light Theme SaaS UI**: Clean slate palette with Inter font, responsive layout, and audit logging.

## Project Structure
```
.
├── backend/
│   ├── bankers.c          # Core Banker's Algorithm implementation in C
│   ├── bankers.h          # Function definitions and constants
│   ├── libbankers.so      # Compiled shared library for ctypes integration
│   ├── main.c             # Standalone C test program
│   ├── Makefile           # GCC build configuration
│   └── server.py          # Flask REST API connecting C core to frontend
├── frontend/
│   ├── index.html         # SaaS dashboard layout
│   ├── script.js          # SVG RAG rendering, pan/zoom, animation, and API hooks
│   └── style.css          # Premium Light Theme styles and animations
├── tests/
│   ├── test_debug.py      # Core endpoint and error handling tests
│   └── test_dynamic_configurations.py  # Multi-dimension configuration tests
├── streamlit_app.py       # Standalone Streamlit Cloud application
├── requirements.txt       # Python dependencies
├── packages.txt           # Linux packages for Streamlit Cloud (GCC build tools)
└── README.md
```

## Running the Application

### Option 1: Flask Web Dashboard (WSL / Linux)
```bash
cd backend
python server.py
```
Open your browser at `http://127.0.0.1:5000`.

### Option 2: Streamlit Application
```bash
streamlit run streamlit_app.py
```

### Option 3: Standalone C Binary Verification
```bash
cd backend
make clean && make
./bankers
```

## Running Automated Tests
```bash
python tests/test_dynamic_configurations.py
python tests/test_debug.py
```
