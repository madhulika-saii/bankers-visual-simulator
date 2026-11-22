
import os
import ctypes
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Load the compiled C shared library
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LIBRARY_PATH = os.path.join(BASE_DIR, "libbankers.so")

FRONTEND_DIR = os.path.abspath(
    os.path.join(BASE_DIR, "..", "frontend")
)

@app.route("/")
def home():
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.route("/<path:filename>")
def frontend_files(filename):
    return send_from_directory(FRONTEND_DIR, filename)

bankers = ctypes.CDLL(LIBRARY_PATH)

MAX_P = 10
MAX_R = 10

# C-compatible data types
Vector = ctypes.c_int * MAX_R
Matrix = (ctypes.c_int * MAX_R) * MAX_P
Sequence = ctypes.c_int * MAX_P

# Configure C function signatures
bankers.calculateNeed.argtypes = [
    ctypes.c_int, ctypes.c_int,
    Matrix, Matrix, Matrix
]
bankers.calculateNeed.restype = ctypes.c_int

bankers.safetyAlgorithm.argtypes = [
    ctypes.c_int, ctypes.c_int,
    Matrix, Matrix, Vector, Sequence
]
bankers.safetyAlgorithm.restype = ctypes.c_int

bankers.requestResources.argtypes = [
    ctypes.c_int, ctypes.c_int, ctypes.c_int,
    Vector, Matrix, Matrix, Vector
]
bankers.requestResources.restype = ctypes.c_int

bankers.releaseResources.argtypes = [
    ctypes.c_int, ctypes.c_int,
    Vector, Matrix, Matrix, Vector
]
bankers.releaseResources.restype = ctypes.c_int

bankers.init_preset_3x2.argtypes = [
    ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int),
    Vector, Matrix, Matrix, Matrix, Vector
]
bankers.init_preset_3x2.restype = ctypes.c_int

bankers.init_preset_6x4.argtypes = [
    ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int),
    Vector, Matrix, Matrix, Matrix, Vector
]
bankers.init_preset_6x4.restype = ctypes.c_int

# Persistent simulation state
state = None


def parse_process_id(val, max_n):
    """Parse process identifier, accepting 0-based integer (0, 1, ...) or label ('P0', 'p1', etc.)."""
    if val is None:
        raise ValueError("Process ID is required")
    if isinstance(val, str):
        val = val.strip()
        if val.upper().startswith("P"):
            val = val[1:]
    val_int = int(val)
    if not (0 <= val_int < max_n):
        raise ValueError(f"Process P{val_int} does not exist (valid: P0 to P{max_n - 1})")
    return val_int


def get_state():
    if state is None:
        return None

    n = state["n"]
    m = state["m"]

    return {
        "processes": n,
        "resources": m,
        "allocation": [
            [state["allocation"][i][j] for j in range(m)]
            for i in range(n)
        ],
        "maximum": [
            [state["maximum"][i][j] for j in range(m)]
            for i in range(n)
        ],
        "need": [
            [state["need"][i][j] for j in range(m)]
            for i in range(n)
        ],
        "available": [
            state["available"][j] for j in range(m)
        ],
        "total": state["total"]
    }


@app.route("/api/initialize", methods=["POST"])
def initialize():
    global state

    data = request.get_json(silent=True) or {}
    preset = data.get("preset")

    # Fast path for C presets
    if preset in ("3x2", "6x4"):
        n_c = ctypes.c_int()
        m_c = ctypes.c_int()
        alloc = Matrix()
        maximum_matrix = Matrix()
        need = Matrix()
        available = Vector()
        total_vec = Vector()

        if preset == "3x2":
            bankers.init_preset_3x2(ctypes.byref(n_c), ctypes.byref(m_c), total_vec, alloc, maximum_matrix, need, available)
        else:
            bankers.init_preset_6x4(ctypes.byref(n_c), ctypes.byref(m_c), total_vec, alloc, maximum_matrix, need, available)

        n = n_c.value
        m = m_c.value
        total = [total_vec[j] for j in range(m)]

        state = {
            "n": n,
            "m": m,
            "total": total,
            "allocation": alloc,
            "maximum": maximum_matrix,
            "need": need,
            "available": available
        }
        return jsonify({
            "message": f"Simulation initialized with {preset} configuration",
            "state": get_state()
        })

    try:
        n = int(data["processes"])
        m = int(data["resources"])

        if not (1 <= n <= MAX_P and 1 <= m <= MAX_R):
            return jsonify({"error": f"Invalid dimensions. Supported limits: Processes 1..{MAX_P}, Resources 1..{MAX_R}"}), 400

        total = data["total"]
        allocation = data["allocation"]
        maximum = data["maximum"]

        if len(total) != m or len(allocation) != n or len(maximum) != n:
            return jsonify({"error": "Incorrect input dimensions"}), 400

        total = [int(x) for x in total]

        if any(x < 0 for x in total):
            return jsonify({"error": "Negative resource count"}), 400

        alloc = Matrix()
        maximum_matrix = Matrix()
        need = Matrix()
        available = Vector()

        for i in range(n):
            if len(allocation[i]) != m or len(maximum[i]) != m:
                return jsonify({"error": "Incorrect matrix dimensions"}), 400

            for j in range(m):
                a = int(allocation[i][j])
                mx = int(maximum[i][j])

                if a < 0 or mx < 0 or mx < a:
                    return jsonify({"error": f"Invalid input for P{i}, R{j}: Allocation ({a}) cannot exceed Maximum ({mx}) or be negative"}), 400

                alloc[i][j] = a
                maximum_matrix[i][j] = mx

        for j in range(m):
            used = sum(alloc[i][j] for i in range(n))

            if used > total[j]:
                return jsonify({"error": f"Resource R{j}: Total allocated ({used}) exceeds total instances ({total[j]})"}), 400

            available[j] = total[j] - used

        result = bankers.calculateNeed(
            n, m, alloc, maximum_matrix, need
        )

        if not result:
            return jsonify({"error": "Need calculation failed in C backend"}), 400

        state = {
            "n": n,
            "m": m,
            "total": total,
            "allocation": alloc,
            "maximum": maximum_matrix,
            "need": need,
            "available": available
        }

        return jsonify({
            "message": f"Simulation initialized with {n} processes and {m} resources",
            "state": get_state()
        })

    except (KeyError, TypeError, ValueError) as error:
        return jsonify({"error": str(error)}), 400


@app.route("/api/state", methods=["GET"])
def current_state():
    if state is None:
        return jsonify({"error": "Initialize the simulation first"}), 400

    return jsonify(get_state())


@app.route("/api/safety", methods=["POST"])
def safety():
    if state is None:
        return jsonify({"error": "Initialize the simulation first"}), 400

    sequence = Sequence()

    result = bankers.safetyAlgorithm(
        state["n"],
        state["m"],
        state["allocation"],
        state["need"],
        state["available"],
        sequence
    )

    safe_sequence = (
        [f"P{sequence[i]}" for i in range(state["n"])]
        if result else []
    )

    return jsonify({
        "safe": bool(result),
        "safe_sequence": safe_sequence,
        "state": get_state()
    })


@app.route("/api/request", methods=["POST"])
def resource_request():
    if state is None:
        return jsonify({"error": "Initialize the simulation first"}), 400

    data = request.get_json(silent=True) or {}

    try:
        process = parse_process_id(data.get("process"), state["n"])
        values = data.get("request")

        if values is None:
            return jsonify({"error": "Request vector is required"}), 400

        if not isinstance(values, list) or len(values) != state["m"]:
            return jsonify({
                "error": f"Request vector must contain exactly {state['m']} numbers (one per resource R0..R{state['m']-1})"
            }), 400

        values = [int(x) for x in values]

        if any(x < 0 for x in values):
            return jsonify({"error": "Request values cannot be negative"}), 400

        if all(x == 0 for x in values):
            return jsonify({"error": "Request vector cannot be all zeros"}), 400

        # Detailed pre-checks for specific rejection reasons
        for j in range(state["m"]):
            if values[j] > state["need"][process][j]:
                return jsonify({
                    "granted": False,
                    "message": f"Request denied: Exceeds Maximum Claim for R{j} (Requested: {values[j]}, Need: {state['need'][process][j]})",
                    "reason": "exceeds_need",
                    "resource": j,
                    "state": get_state()
                })

        for j in range(state["m"]):
            if values[j] > state["available"][j]:
                return jsonify({
                    "granted": False,
                    "message": f"Request denied: Insufficient Available resources for R{j} (Requested: {values[j]}, Available: {state['available'][j]})",
                    "reason": "insufficient_available",
                    "resource": j,
                    "state": get_state()
                })

        request_vector = Vector()
        for j in range(state["m"]):
            request_vector[j] = values[j]

        # Call C implementation which tentatively allocates, checks safety, and rolls back if unsafe
        result = bankers.requestResources(
            process,
            state["n"],
            state["m"],
            request_vector,
            state["allocation"],
            state["need"],
            state["available"]
        )

        return jsonify({
            "granted": bool(result),
            "message": f"Request granted to P{process}" if result else f"Request denied for P{process}: Allocation leads to an unsafe state (Deadlock Risk). Rolled back.",
            "reason": "granted" if result else "unsafe_state",
            "state": get_state()
        })

    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except (KeyError, TypeError) as error:
        return jsonify({"error": str(error)}), 400


@app.route("/api/release", methods=["POST"])
def resource_release():
    if state is None:
        return jsonify({"error": "Initialize the simulation first"}), 400

    data = request.get_json(silent=True) or {}

    try:
        process = parse_process_id(data.get("process"), state["n"])
        values = data.get("release")

        if values is None:
            return jsonify({"error": "Release vector is required"}), 400

        if not isinstance(values, list) or len(values) != state["m"]:
            return jsonify({
                "error": f"Release vector must contain exactly {state['m']} numbers (one per resource R0..R{state['m']-1})"
            }), 400

        values = [int(x) for x in values]

        if any(x < 0 for x in values):
            return jsonify({"error": "Release values cannot be negative"}), 400

        if all(x == 0 for x in values):
            return jsonify({"error": "Release vector cannot be all zeros"}), 400

        # Detailed pre-checks for release validation
        for j in range(state["m"]):
            if values[j] > state["allocation"][process][j]:
                return jsonify({
                    "released": False,
                    "message": f"Release rejected: Process P{process} cannot release {values[j]} of R{j} (Currently allocated: {state['allocation'][process][j]})",
                    "reason": "exceeds_allocation",
                    "resource": j,
                    "state": get_state()
                })

        release_vector = Vector()
        for j in range(state["m"]):
            release_vector[j] = values[j]

        # Call C implementation to release resources
        result = bankers.releaseResources(
            process,
            state["m"],
            release_vector,
            state["allocation"],
            state["need"],
            state["available"]
        )

        return jsonify({
            "released": bool(result),
            "message": f"Resources successfully released by P{process}" if result else f"Release rejected for P{process}",
            "state": get_state()
        })

    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except (KeyError, TypeError) as error:
        return jsonify({"error": str(error)}), 400


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
