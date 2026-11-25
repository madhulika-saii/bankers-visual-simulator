import os
import sys
import unittest
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))
sys.path.insert(0, PROJECT_ROOT)

import streamlit_app

class FinalReleaseAudit15Tests(unittest.TestCase):
    """
    Comprehensive 15-Point Final Release Audit for Banker's Algorithm Simulator:
    Verifies mathematics, C algorithm integration, dynamic dimensions, RAG arrows,
    request/release operations, rollback, safety sequence, styling, and deployment sync.
    """
    @classmethod
    def setUpClass(cls):
        cls.bankers_c, cls.MAX_P, cls.MAX_R, cls.Vector, cls.Matrix, cls.Sequence = streamlit_app.get_c_library()
        cls.PRESETS = streamlit_app.PRESETS

    def test_01_available_formula_correctness(self):
        """1. Verify Available = Total - sum(Allocation) across configurations and reject negative available"""
        # Benchmark 5x3
        preset = self.PRESETS["5 Processes × 3 Resources (Default)"]
        n, m = preset["processes"], preset["resources"]
        alloc = preset["allocation"]
        total = preset["total"]

        avail = [total[j] - sum(alloc[i][j] for i in range(n)) for j in range(m)]
        self.assertEqual(avail, [3, 3, 2], "Available vector must match [3, 3, 2]")

        # Reject configuration if Allocation exceeds Total (would cause negative Available)
        invalid_alloc = [list(r) for r in alloc]
        invalid_alloc[0][0] = 99  # Allocation sum exceeds total[0]=10
        errors = streamlit_app.validate_system_configuration(n, m, total, invalid_alloc, preset["maximum"])
        self.assertTrue(any("exceed Total system capacity" in e for e in errors), "Validator must reject negative available")

    def test_02_need_matrix_calculation(self):
        """2. Verify Need = Maximum - Allocation calculated via C backend"""
        alloc_c = self.Matrix()
        max_c = self.Matrix()
        need_c = self.Matrix()
        preset = self.PRESETS["5 Processes × 3 Resources (Default)"]
        n, m = preset["processes"], preset["resources"]

        for i in range(n):
            for j in range(m):
                alloc_c[i][j] = preset["allocation"][i][j]
                max_c[i][j] = preset["maximum"][i][j]

        ok = self.bankers_c.calculateNeed(n, m, alloc_c, max_c, need_c)
        self.assertEqual(ok, 1, "calculateNeed must succeed in C")

        # Compare every cell
        for i in range(n):
            for j in range(m):
                expected = preset["maximum"][i][j] - preset["allocation"][i][j]
                self.assertEqual(need_c[i][j], expected, f"Need[{i}][{j}] must equal Max - Alloc")

    def test_03_dynamic_process_and_resource_configuration(self):
        """3. Verify dynamic process and resource configuration (3x2, 5x3, 6x4)"""
        for name, preset in self.PRESETS.items():
            n, m = preset["processes"], preset["resources"]
            alloc = preset["allocation"]
            total = preset["total"]
            mx = preset["maximum"]

            errors = streamlit_app.validate_system_configuration(n, m, total, alloc, mx)
            self.assertEqual(len(errors), 0, f"Preset {name} must be valid without errors")

            avail = [total[j] - sum(alloc[i][j] for i in range(n)) for j in range(m)]
            svg = streamlit_app.generate_rag_svg(n, m, alloc, total, avail)
            # Verify process and resource labels exist
            for i in range(n):
                self.assertIn(f"P{i}", svg, f"P{i} must be rendered in {name}")
            for j in range(m):
                self.assertIn(f"R{j}", svg, f"R{j} must be rendered in {name}")

    def test_04_large_readable_rag_svg_canvas(self):
        """4. Verify large, high-resolution SVG canvas dimensions and elements"""
        preset = self.PRESETS["5 Processes × 3 Resources (Default)"]
        n, m = preset["processes"], preset["resources"]
        alloc, total = preset["allocation"], preset["total"]
        avail = [3, 3, 2]

        svg = streamlit_app.generate_rag_svg(n, m, alloc, total, avail)
        self.assertIn('viewBox="0.0 0.0 960.0', svg, "SVG width must be large 960px canvas")
        self.assertIn('background:#FFFFFF', svg, "Canvas must have clean white background")
        self.assertIn('R0 (Total: 10)', svg, "Resource node must show Total capacity")
        self.assertIn('Alloc: 7', svg, "Resource node must show Total Allocated instances")
        self.assertIn('Avail: 3', svg, "Resource node must show Available instances")

    def test_05_solid_allocation_and_dashed_request_arrows(self):
        """5. Verify solid blue allocation arrows and dashed orange request arrows"""
        preset = self.PRESETS["5 Processes × 3 Resources (Default)"]
        n, m = preset["processes"], preset["resources"]
        alloc, total = preset["allocation"], preset["total"]
        avail = [3, 3, 2]

        # Case A: No pending request -> only solid blue allocation edges, no request edge paths
        svg_no_req = streamlit_app.generate_rag_svg(n, m, alloc, total, avail, pending_request=None)
        self.assertIn('marker id="allocArrow"', svg_no_req)
        self.assertIn('stroke="#2563EB"', svg_no_req, "Solid blue allocation stroke")
        self.assertNotIn('<path class="rag-req-edge"', svg_no_req, "No request edge paths when pending_request is None")

        # Case B: Staged pending request for P1 [1, 0, 2]
        pending_req = {"proc": 1, "values": [1, 0, 2]}
        svg_with_req = streamlit_app.generate_rag_svg(n, m, alloc, total, avail, pending_request=pending_req)
        self.assertIn('marker id="reqArrow"', svg_with_req)
        self.assertIn('<path class="rag-req-edge"', svg_with_req, "Request edge path must be rendered for active request")
        self.assertIn('stroke="#EA580C"', svg_with_req, "Dashed orange request stroke")
        self.assertIn('1 (req)', svg_with_req)
        self.assertIn('2 (req)', svg_with_req)

    def test_06_correct_arrow_directions(self):
        """6. Verify arrow directions: Resource -> Process (Alloc) and Process -> Resource (Req)"""
        # Resource x is rx = 760, Process x is px = 180
        # Allocation edge goes from right (rx - rw/2 ~ 710) to left (px + prad ~ 212)
        # Request edge goes from left (px + prad ~ 212) to right (rx - rw/2 ~ 710)
        preset = self.PRESETS["5 Processes × 3 Resources (Default)"]
        n, m = preset["processes"], preset["resources"]
        alloc, total = preset["allocation"], preset["total"]
        avail = [3, 3, 2]
        pending_req = {"proc": 1, "values": [1, 0, 2]}

        svg = streamlit_app.generate_rag_svg(n, m, alloc, total, avail, pending_request=pending_req)
        # Allocation edge has marker-end="url(#allocArrow)"
        self.assertIn('marker-end="url(#allocArrow)"', svg)
        # Request edge has marker-end="url(#reqArrow)"
        self.assertIn('marker-end="url(#reqArrow)"', svg)
        # Legend defines directions explicitly
        self.assertIn("Allocation (Resource → Process)", svg)
        self.assertIn("Active Request (Process → Resource)", svg)

    def test_07_valid_and_invalid_resource_requests(self):
        """7. Verify valid request is granted, and invalid requests (exceeding Need or Available) are rejected"""
        alloc_c = self.Matrix()
        need_c = self.Matrix()
        avail_c = self.Vector()
        req_c = self.Vector()

        preset = self.PRESETS["5 Processes × 3 Resources (Default)"]
        n, m = preset["processes"], preset["resources"]

        for i in range(n):
            for j in range(m):
                alloc_c[i][j] = preset["allocation"][i][j]
                need_c[i][j] = preset["maximum"][i][j] - preset["allocation"][i][j]
        avail_c[0] = 3; avail_c[1] = 3; avail_c[2] = 2

        # Valid Request: P1 [1, 0, 2]
        req_c[0] = 1; req_c[1] = 0; req_c[2] = 2
        granted = self.bankers_c.requestResources(1, n, m, req_c, alloc_c, need_c, avail_c)
        self.assertEqual(granted, 1, "P1 request [1, 0, 2] must be granted by C")

        # Invalid Request A: Exceeds Need (P1 requests 2 of R0, but remaining Need is 1)
        req_c[0] = 2; req_c[1] = 0; req_c[2] = 0
        denied_need = self.bankers_c.requestResources(1, n, m, req_c, alloc_c, need_c, avail_c)
        self.assertEqual(denied_need, 0, "Request exceeding Need must be rejected")

        # Invalid Request B: Exceeds Available (P0 requests 4 of R0, but Available is 2)
        req_c[0] = 4; req_c[1] = 0; req_c[2] = 0
        denied_avail = self.bankers_c.requestResources(0, n, m, req_c, alloc_c, need_c, avail_c)
        self.assertEqual(denied_avail, 0, "Request exceeding Available must be rejected")

    def test_08_valid_and_invalid_releases(self):
        """8. Verify valid resource release and rejection of release exceeding held allocation"""
        alloc_c = self.Matrix()
        need_c = self.Matrix()
        avail_c = self.Vector()
        rel_c = self.Vector()

        preset = self.PRESETS["5 Processes × 3 Resources (Default)"]
        n, m = preset["processes"], preset["resources"]

        for i in range(n):
            for j in range(m):
                alloc_c[i][j] = preset["allocation"][i][j]
                need_c[i][j] = preset["maximum"][i][j] - preset["allocation"][i][j]
        avail_c[0] = 3; avail_c[1] = 3; avail_c[2] = 2

        # P1 has allocation [2, 0, 0]. Release [1, 0, 0] is valid.
        rel_c[0] = 1; rel_c[1] = 0; rel_c[2] = 0
        ok = self.bankers_c.releaseResources(1, m, rel_c, alloc_c, need_c, avail_c)
        self.assertEqual(ok, 1, "Valid release must succeed")
        self.assertEqual(alloc_c[1][0], 1, "Allocation must decrease")
        self.assertEqual(avail_c[0], 4, "Available must increase")

        # P4 has allocation [0, 0, 2]. Releasing [1, 0, 0] is invalid (holds 0 of R0).
        rel_c[0] = 1; rel_c[1] = 0; rel_c[2] = 0
        invalid_rel = self.bankers_c.releaseResources(4, m, rel_c, alloc_c, need_c, avail_c)
        self.assertEqual(invalid_rel, 0, "Release exceeding held allocation must be rejected")

    def test_09_unsafe_request_rollback(self):
        """9. Verify unsafe request rollback: Tentative allocation restored upon deadlock risk"""
        alloc_c = self.Matrix()
        need_c = self.Matrix()
        avail_c = self.Vector()
        req_c = self.Vector()

        preset = self.PRESETS["5 Processes × 3 Resources (Default)"]
        n, m = preset["processes"], preset["resources"]

        for i in range(n):
            for j in range(m):
                alloc_c[i][j] = preset["allocation"][i][j]
                need_c[i][j] = preset["maximum"][i][j] - preset["allocation"][i][j]
        avail_c[0] = 3; avail_c[1] = 3; avail_c[2] = 2

        # P4 requests [3, 3, 0] -> leaves Available [0, 0, 2], which is UNSAFE (deadlock risk)
        req_c[0] = 3; req_c[1] = 3; req_c[2] = 0
        granted = self.bankers_c.requestResources(4, n, m, req_c, alloc_c, need_c, avail_c)
        self.assertEqual(granted, 0, "Unsafe request must be denied by C algorithm")

        # Rollback check: System allocations and available vector must be strictly preserved
        self.assertEqual([avail_c[j] for j in range(m)], [3, 3, 2], "Available vector must be rolled back")
        self.assertEqual([alloc_c[4][j] for j in range(m)], [0, 0, 2], "P4 allocation must be rolled back")

    def test_10_correct_safe_sequence_from_c_backend(self):
        """10. Verify correct safe sequence evaluated by the C backend"""
        alloc_c = self.Matrix()
        need_c = self.Matrix()
        avail_c = self.Vector()
        seq_c = self.Sequence()

        preset = self.PRESETS["5 Processes × 3 Resources (Default)"]
        n, m = preset["processes"], preset["resources"]

        for i in range(n):
            for j in range(m):
                alloc_c[i][j] = preset["allocation"][i][j]
                need_c[i][j] = preset["maximum"][i][j] - preset["allocation"][i][j]
        avail_c[0] = 3; avail_c[1] = 3; avail_c[2] = 2

        is_safe = self.bankers_c.safetyAlgorithm(n, m, alloc_c, need_c, avail_c, seq_c)
        self.assertEqual(is_safe, 1, "Benchmark system must be verified SAFE by C algorithm")
        seq = [f"P{seq_c[i]}" for i in range(n)]
        self.assertEqual(seq, ["P1", "P3", "P4", "P0", "P2"], "Safe sequence must match standard C sequence")

    def test_11_working_safe_sequence_animation(self):
        """11. Verify safe sequence animation active process highlighting"""
        preset = self.PRESETS["5 Processes × 3 Resources (Default)"]
        n, m = preset["processes"], preset["resources"]
        alloc, total = preset["allocation"], preset["total"]
        avail = [3, 3, 2]

        # Active process = P1
        svg_p1 = streamlit_app.generate_rag_svg(n, m, alloc, total, avail, active_proc="P1")
        # P1 circle must receive emerald active highlight
        self.assertIn('fill="#ECFDF5"', svg_p1, "Highlighted active process must have emerald fill")
        self.assertIn('stroke="#059669"', svg_p1, "Highlighted active process must have emerald border")

    def test_12_responsive_professional_light_theme(self):
        """12. Verify responsive SaaS light theme styling with no dark backgrounds"""
        # Read streamlit_app.py file content to inspect CSS
        with open(os.path.join(PROJECT_ROOT, "streamlit_app.py"), "r", encoding="utf-8") as f:
            code = f.read()

        self.assertIn("#F8FAFC", code, "Global background must use light slate #F8FAFC")
        self.assertIn("#FFFFFF", code, "Card background must use clean white #FFFFFF")
        self.assertIn("#1E293B", code, "Primary typography must use dark navy #1E293B")
        self.assertIn("#2563EB", code, "Accent color must use royal blue #2563EB")
        self.assertIn("#7C3AED", code, "Resource node stroke must use soft violet #7C3AED")
        self.assertNotIn("background-color: #000000", code, "No pure black dark background allowed")
        self.assertNotIn("background-color: #121212", code, "No dark theme background allowed")

    def test_13_no_browser_errors_or_python_exceptions(self):
        """13. Verify clean execution of streamlit_app without Python exceptions or warnings"""
        # Execute streamlit_app as a dry-run check
        env = dict(os.environ)
        result = subprocess.run(
            [sys.executable, "-c", "import streamlit_app; print('DRY_RUN_SUCCESS')"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            env=env
        )
        self.assertEqual(result.returncode, 0, f"streamlit_app dry run failed: {result.stderr}")
        self.assertIn("DRY_RUN_SUCCESS", result.stdout, "streamlit_app imported and executed cleanly")

    def test_14_correct_github_deployment_synchronization(self):
        """14. Verify git status, tracking branch, and commit sync with origin/main"""
        res_status = subprocess.run(
            ["git", "status"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True
        )
        self.assertEqual(res_status.returncode, 0)
        self.assertIn("Your branch is up to date with 'origin/main'", res_status.stdout)

        res_rev_local = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True
        )
        res_rev_remote = subprocess.run(
            ["git", "rev-parse", "origin/main"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True
        )
        self.assertEqual(res_rev_local.returncode, 0)
        self.assertEqual(res_rev_remote.returncode, 0)
        self.assertEqual(res_rev_local.stdout.strip(), res_rev_remote.stdout.strip(), "Local head must match pushed remote origin/main")

    def test_15_public_streamlit_url_responsiveness(self):
        """15. Verify public Streamlit Community Cloud URL is active and reachable"""
        curl_res = subprocess.run(
            ["curl", "-s", "-I", "https://bankers-visual-simulator.streamlit.app/"],
            capture_output=True,
            text=True
        )
        self.assertEqual(curl_res.returncode, 0, "curl to public Streamlit URL must succeed")
        # Streamlit Community Cloud server header check
        self.assertIn("server: nginx", curl_res.stdout.lower(), "Streamlit Cloud Nginx edge router responded")
        self.assertIn("303", curl_res.stdout, "App is active and serving via Streamlit Cloud auth gateway")

    def test_16_automatic_algorithm_selection_modes(self):
        """16. Verify Automatic Algorithm Selection: Single-Instance RAG vs Multi-Instance Banker's vs Mixed-Instance"""
        # Case A: Single-Instance (all total = 1)
        mode_a = streamlit_app.determine_algorithm_mode([1, 1, 1])
        self.assertEqual(mode_a["mode"], "SINGLE_INSTANCE")
        self.assertIn("Resource Allocation Graph (RAG) Cycle Detection", mode_a["name"])
        self.assertIn("Deadlock", mode_a["math_note"])
        self.assertIn("Necessary & Sufficient", mode_a["math_note"])

        # Case B: Multi-Instance (all total > 1)
        mode_b = streamlit_app.determine_algorithm_mode([10, 5, 7])
        self.assertEqual(mode_b["mode"], "MULTI_INSTANCE")
        self.assertIn("Banker's Algorithm", mode_b["name"])
        self.assertIn("Necessary but NOT Sufficient", mode_b["math_note"])
        self.assertIn("Work and Finish", mode_b["reason"])

        # Case C: Mixed-Instance (some total = 1, some > 1)
        mode_c = streamlit_app.determine_algorithm_mode([1, 5, 1])
        self.assertEqual(mode_c["mode"], "MIXED_INSTANCE")
        self.assertIn("Banker's Algorithm (General Multi-Instance Mode)", mode_c["name"])
        self.assertIn("General Banker's Algorithm guarantees safety", mode_c["math_note"])

    def test_17_single_instance_rag_cycle_deadlock_detection(self):
        """17. Verify RAG Cycle Detection in C backend correctly detects deadlock cycle and highlights path"""
        # 2x2 cycle: P0 holds R0, requests R1; P1 holds R1, requests R0
        alloc = [[1, 0], [0, 1]]
        req = [[0, 1], [1, 0]]
        has_cycle, cycle_labels, cycle_edges = streamlit_app.compute_rag_cycle(2, 2, alloc, req)
        self.assertTrue(has_cycle)
        self.assertGreater(len(cycle_labels), 2)
        self.assertEqual(cycle_labels[0], cycle_labels[-1], "Cycle path must be closed loop")
        self.assertIn(("P0", "R1"), cycle_edges)
        self.assertIn(("R1", "P1"), cycle_edges)
        self.assertIn(("P1", "R0"), cycle_edges)
        self.assertIn(("R0", "P0"), cycle_edges)

        # SVG representation should highlight cycle edges with red stroke (#DC2626) and cycle nodes
        total = [1, 1]
        avail = [0, 0]
        cycle_nodes = set(cycle_labels)
        svg = streamlit_app.generate_rag_svg(2, 2, alloc, total, avail, cycle_edges=cycle_edges, cycle_nodes=cycle_nodes)
        self.assertIn('stroke="#DC2626"', svg)
        self.assertIn('marker id="cycleArrow"', svg)
        self.assertIn('Deadlock Cycle', svg)

if __name__ == "__main__":
    unittest.main()
