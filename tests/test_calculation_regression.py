import os
import sys
import unittest

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))
sys.path.insert(0, PROJECT_ROOT)

import streamlit_app

class CriticalCalculationRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bankers_c, cls.MAX_P, cls.MAX_R, cls.Vector, cls.Matrix, cls.Sequence = streamlit_app.get_c_library()
        cls.PRESETS = streamlit_app.PRESETS

    def test_01_available_vector_calculation(self):
        """1. Available vector calculation: Available[j] = Total[j] - sum(Allocation[i][j])"""
        preset = self.PRESETS["5 Processes × 3 Resources (Default)"]
        n = preset["processes"]
        m = preset["resources"]
        alloc = preset["allocation"]
        total = preset["total"] # [10, 5, 7]

        # Allocated sum for each resource:
        # R0: 0 + 2 + 3 + 2 + 0 = 7. Avail = 10 - 7 = 3
        # R1: 1 + 0 + 0 + 1 + 0 = 2. Avail = 5 - 2 = 3
        # R2: 0 + 0 + 2 + 1 + 2 = 5. Avail = 7 - 5 = 2
        for j in range(m):
            alloc_j = sum(alloc[i][j] for i in range(n))
            avail_j = total[j] - alloc_j
            self.assertGreaterEqual(avail_j, 0, f"Available for R{j} must be non-negative")
            if j == 0: self.assertEqual(avail_j, 3)
            elif j == 1: self.assertEqual(avail_j, 3)
            elif j == 2: self.assertEqual(avail_j, 2)

    def test_02_negative_allocation_rejection(self):
        """2. Negative allocation rejection in configuration validation"""
        invalid_alloc = [
            [-1, 1, 0],
            [2, 0, 0],
            [3, 0, 2],
            [2, 1, 1],
            [0, 0, 2]
        ]
        errors = streamlit_app.validate_system_configuration(
            5, 3, [10, 5, 7], invalid_alloc, self.PRESETS["5 Processes × 3 Resources (Default)"]["maximum"]
        )
        self.assertTrue(any("cannot be negative" in e for e in errors))

    def test_03_allocation_exceeding_total_resources_rejection(self):
        """3. Allocation exceeding total resources rejection (preventing negative available)"""
        # If total is [5, 2, 5], allocated is [7, 2, 5] -> R0 allocated exceeds total (5 - 7 = -2)
        errors = streamlit_app.validate_system_configuration(
            5, 3, [5, 2, 5], self.PRESETS["5 Processes × 3 Resources (Default)"]["allocation"], self.PRESETS["5 Processes × 3 Resources (Default)"]["maximum"]
        )
        self.assertTrue(any("exceed Total system capacity" in e and "Available would be negative" in e for e in errors))

    def test_04_incorrect_matrix_dimensions_rejection(self):
        """4. Incorrect matrix dimensions rejection"""
        # 4 rows instead of 5
        errors = streamlit_app.validate_system_configuration(
            5, 3, [10, 5, 7], [[0, 1, 0]] * 4, [[7, 5, 3]] * 5
        )
        self.assertTrue(any("Dimension mismatch" in e for e in errors))

    def test_05_correct_need_calculation(self):
        """5. Correct Need calculation: Need = Maximum - Allocation in C"""
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
        self.assertEqual(ok, 1)

        for i in range(n):
            for j in range(m):
                expected = preset["maximum"][i][j] - preset["allocation"][i][j]
                self.assertEqual(need_c[i][j], expected)

    def test_06_valid_resource_request(self):
        """6. Valid resource request: P1 [1, 0, 2] granted by C"""
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
        req_c[0] = 1; req_c[1] = 0; req_c[2] = 2

        granted = self.bankers_c.requestResources(1, n, m, req_c, alloc_c, need_c, avail_c)
        self.assertEqual(granted, 1)
        self.assertEqual([avail_c[j] for j in range(m)], [2, 3, 0])

    def test_07_request_exceeding_need_rejection(self):
        """7. Request exceeding Need rejected"""
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
        # P1 Need is [1, 2, 2]. Request [2, 0, 0] exceeds Need for R0
        req_c[0] = 2; req_c[1] = 0; req_c[2] = 0

        granted = self.bankers_c.requestResources(1, n, m, req_c, alloc_c, need_c, avail_c)
        self.assertEqual(granted, 0)

    def test_08_request_exceeding_available_rejection(self):
        """8. Request exceeding Available rejected"""
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
        # P0 Need is [7, 4, 3]. Request [4, 0, 0] exceeds Available[0] = 3
        req_c[0] = 4; req_c[1] = 0; req_c[2] = 0

        granted = self.bankers_c.requestResources(0, n, m, req_c, alloc_c, need_c, avail_c)
        self.assertEqual(granted, 0)

    def test_09_unsafe_request_rollback(self):
        """9. Unsafe request rollback: Tentative allocation restored on deadlock risk"""
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
        # P4 requests [3, 3, 0] -> leaves Available [0, 0, 2], which is UNSAFE
        req_c[0] = 3; req_c[1] = 3; req_c[2] = 0

        granted = self.bankers_c.requestResources(4, n, m, req_c, alloc_c, need_c, avail_c)
        self.assertEqual(granted, 0)
        # Rollback check
        self.assertEqual([avail_c[j] for j in range(m)], [3, 3, 2])
        self.assertEqual([alloc_c[4][j] for j in range(m)], [0, 0, 2])

    def test_10_valid_resource_release(self):
        """10. Valid resource release: P1 releases [1, 0, 0]"""
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
        rel_c[0] = 1; rel_c[1] = 0; rel_c[2] = 0

        ok = self.bankers_c.releaseResources(1, m, rel_c, alloc_c, need_c, avail_c)
        self.assertEqual(ok, 1)
        self.assertEqual([avail_c[j] for j in range(m)], [4, 3, 2])
        self.assertEqual([alloc_c[1][j] for j in range(m)], [1, 0, 0])

    def test_11_graph_synchronization(self):
        """11. Graph synchronization: Resource nodes show exact Total, Allocated, and Available counts"""
        total = [10, 5, 7]
        alloc = [
            [0, 1, 0],
            [2, 0, 0],
            [3, 0, 2],
            [2, 1, 1],
            [0, 0, 2]
        ]
        avail = [3, 3, 2]

        svg = streamlit_app.generate_rag_svg(5, 3, alloc, total, avail)
        # Verify labels inside SVG
        self.assertIn("R0 (Total: 10)", svg)
        self.assertIn("Alloc: 7", svg)
        self.assertIn("Avail: 3", svg)

        self.assertIn("R1 (Total: 5)", svg)
        self.assertIn("Alloc: 2", svg)
        self.assertIn("Avail: 3", svg)

        self.assertIn("R2 (Total: 7)", svg)
        self.assertIn("Alloc: 5", svg)
        self.assertIn("Avail: 2", svg)

    def test_12_safety_sequence_correctness(self):
        """12. Safety sequence correctness in C"""
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
        self.assertEqual(is_safe, 1)
        seq = [f"P{seq_c[i]}" for i in range(n)]
        self.assertEqual(seq, ["P1", "P3", "P4", "P0", "P2"])

    def test_13_solid_allocation_vs_dotted_request_arrows(self):
        """13. Visual distinction: Solid blue allocation arrows and dotted orange request arrows"""
        total = [10, 5, 7]
        alloc = [
            [0, 1, 0],
            [2, 0, 0],
            [3, 0, 2],
            [2, 1, 1],
            [0, 0, 2]
        ]
        avail = [3, 3, 2]

        # Scenario A: No pending request -> Only solid blue allocation edges, no request edges
        svg_no_req = streamlit_app.generate_rag_svg(5, 3, alloc, total, avail, pending_request=None)
        self.assertIn('marker id="allocArrow"', svg_no_req)
        self.assertIn('stroke="#2563EB"', svg_no_req)
        self.assertNotIn('class="rag-req-edge"', svg_no_req)

        # Scenario B: Active pending request for P1 [1, 0, 2]
        pending_req = {"proc": 1, "values": [1, 0, 2]}
        svg_with_req = streamlit_app.generate_rag_svg(5, 3, alloc, total, avail, pending_request=pending_req)

        # Both markers must be present
        self.assertIn('marker id="allocArrow"', svg_with_req)
        self.assertIn('marker id="reqArrow"', svg_with_req)

        # Solid blue allocation edge present
        self.assertIn('stroke="#2563EB"', svg_with_req)
        # Dotted/dashed orange request edge present
        self.assertIn('class="rag-req-edge"', svg_with_req)
        self.assertIn('stroke="#EA580C"', svg_with_req)
        self.assertIn('marker-end="url(#reqArrow)"', svg_with_req)
        self.assertIn('1 (req)', svg_with_req)
        self.assertIn('2 (req)', svg_with_req)

        # Process P1 node should receive the active pending highlight (#EA580C)
        self.assertIn('fill="#C2410C"', svg_with_req)

    def test_14_request_lifecycle_and_rollback_integrity(self):
        """14. Request lifecycle: Pending edge removed on grant, system preserved on rollback"""
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

        # Safe request for P1 [1, 0, 2] -> Granted
        req_c[0] = 1; req_c[1] = 0; req_c[2] = 2
        granted = self.bankers_c.requestResources(1, n, m, req_c, alloc_c, need_c, avail_c)
        self.assertEqual(granted, 1)
        self.assertEqual(alloc_c[1][0], 3)
        self.assertEqual(alloc_c[1][2], 2)
        self.assertEqual(avail_c[0], 2)
        self.assertEqual(avail_c[2], 0)

        # Unsafe request for P4 [2, 3, 0] -> Denied & Rolled back in C (leaves available [0, 0, 0])
        req_c[0] = 2; req_c[1] = 3; req_c[2] = 0
        denied = self.bankers_c.requestResources(4, n, m, req_c, alloc_c, need_c, avail_c)
        self.assertEqual(denied, 0)
        # Check that allocation and available were restored (rolled back)
        self.assertEqual(alloc_c[4][0], 0)
        self.assertEqual(avail_c[0], 2)

    def test_15_graph_zoom_pan_and_legend(self):
        """15. Graph zoom, pan, and legend in SVG"""
        total = [10, 5, 7]
        alloc = [
            [0, 1, 0],
            [2, 0, 0],
            [3, 0, 2],
            [2, 1, 1],
            [0, 0, 2]
        ]
        avail = [3, 3, 2]

        # Verify default viewBox at zoom 1.0, pan 0
        svg_normal = streamlit_app.generate_rag_svg(5, 3, alloc, total, avail, zoom=1.0, pan_x=0, pan_y=0)
        self.assertIn('viewBox="0.0 0.0 960.0', svg_normal)

        # Verify zoomed-in viewBox
        svg_zoomed = streamlit_app.generate_rag_svg(5, 3, alloc, total, avail, zoom=1.5, pan_x=50, pan_y=20)
        # 960 / 1.5 = 640 width, vb_x = (960 - 640)/2 + 50 = 210.0
        self.assertIn('viewBox="210.0', svg_zoomed)

        # Verify Legend items exist
        self.assertIn("Allocation (Resource → Process)", svg_normal)
        self.assertIn("Active Request (Process → Resource)", svg_normal)
        self.assertIn("Process", svg_normal)
        self.assertIn("Res", svg_normal)

if __name__ == "__main__":
    unittest.main()
