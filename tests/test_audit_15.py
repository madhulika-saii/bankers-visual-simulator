import os
import sys
import ctypes
import unittest
import subprocess

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))
sys.path.insert(0, PROJECT_ROOT)

import streamlit_app

class CompleteAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Locate and bind C library exactly as streamlit_app does
        cls.bankers_c, cls.MAX_P, cls.MAX_R, cls.Vector, cls.Matrix, cls.Sequence = streamlit_app.get_c_library()
        cls.PRESETS = streamlit_app.PRESETS

    def test_01_initialize_simulation(self):
        """1. Initialize simulation with standard benchmark and verify C binding"""
        preset = self.PRESETS["5 Processes × 3 Resources (Default)"]
        n = preset["processes"]
        m = preset["resources"]
        alloc = preset["allocation"]
        max_m = preset["maximum"]
        total = preset["total"]

        alloc_c = self.Matrix()
        max_c = self.Matrix()
        need_c = self.Matrix()
        avail_c = self.Vector()

        for i in range(n):
            for j in range(m):
                alloc_c[i][j] = alloc[i][j]
                max_c[i][j] = max_m[i][j]

        for j in range(m):
            used = sum(alloc[i][j] for i in range(n))
            avail_c[j] = total[j] - used

        ok = self.bankers_c.calculateNeed(n, m, alloc_c, max_c, need_c)
        self.assertEqual(ok, 1)
        avail = [avail_c[j] for j in range(m)]
        self.assertEqual(avail, [3, 3, 2])

    def test_02_configure_3_processes_2_resources(self):
        """2. Configure 3 processes and 2 resources"""
        preset = self.PRESETS["3 Processes × 2 Resources"]
        n = preset["processes"]
        m = preset["resources"]
        self.assertEqual(n, 3)
        self.assertEqual(m, 2)

        alloc_c = self.Matrix()
        max_c = self.Matrix()
        need_c = self.Matrix()
        avail_c = self.Vector()
        seq_c = self.Sequence()

        for i in range(n):
            for j in range(m):
                alloc_c[i][j] = preset["allocation"][i][j]
                max_c[i][j] = preset["maximum"][i][j]

        for j in range(m):
            used = sum(preset["allocation"][i][j] for i in range(n))
            avail_c[j] = preset["total"][j] - used

        ok = self.bankers_c.calculateNeed(n, m, alloc_c, max_c, need_c)
        self.assertEqual(ok, 1)
        is_safe = self.bankers_c.safetyAlgorithm(n, m, alloc_c, need_c, avail_c, seq_c)
        self.assertEqual(is_safe, 1)
        seq = [f"P{seq_c[i]}" for i in range(n)]
        self.assertEqual(len(seq), 3)

    def test_03_configure_5_processes_3_resources(self):
        """3. Configure 5 processes and 3 resources"""
        preset = self.PRESETS["5 Processes × 3 Resources (Default)"]
        n = preset["processes"]
        m = preset["resources"]
        self.assertEqual(n, 5)
        self.assertEqual(m, 3)

        alloc_c = self.Matrix()
        max_c = self.Matrix()
        need_c = self.Matrix()
        avail_c = self.Vector()
        seq_c = self.Sequence()

        for i in range(n):
            for j in range(m):
                alloc_c[i][j] = preset["allocation"][i][j]
                max_c[i][j] = preset["maximum"][i][j]

        for j in range(m):
            used = sum(preset["allocation"][i][j] for i in range(n))
            avail_c[j] = preset["total"][j] - used

        ok = self.bankers_c.calculateNeed(n, m, alloc_c, max_c, need_c)
        self.assertEqual(ok, 1)
        is_safe = self.bankers_c.safetyAlgorithm(n, m, alloc_c, need_c, avail_c, seq_c)
        self.assertEqual(is_safe, 1)
        seq = [f"P{seq_c[i]}" for i in range(n)]
        self.assertEqual(seq, ["P1", "P3", "P4", "P0", "P2"])

    def test_04_configure_6_processes_4_resources(self):
        """4. Configure 6 processes and 4 resources"""
        preset = self.PRESETS["6 Processes × 4 Resources"]
        n = preset["processes"]
        m = preset["resources"]
        self.assertEqual(n, 6)
        self.assertEqual(m, 4)

        alloc_c = self.Matrix()
        max_c = self.Matrix()
        need_c = self.Matrix()
        avail_c = self.Vector()
        seq_c = self.Sequence()

        for i in range(n):
            for j in range(m):
                alloc_c[i][j] = preset["allocation"][i][j]
                max_c[i][j] = preset["maximum"][i][j]

        for j in range(m):
            used = sum(preset["allocation"][i][j] for i in range(n))
            avail_c[j] = preset["total"][j] - used

        ok = self.bankers_c.calculateNeed(n, m, alloc_c, max_c, need_c)
        self.assertEqual(ok, 1)
        is_safe = self.bankers_c.safetyAlgorithm(n, m, alloc_c, need_c, avail_c, seq_c)
        self.assertEqual(is_safe, 1)
        seq = [f"P{seq_c[i]}" for i in range(n)]
        self.assertEqual(len(seq), 6)

    def test_05_verify_need_equals_maximum_minus_allocation(self):
        """5. Verify Need = Maximum - Allocation in C implementation"""
        preset = self.PRESETS["5 Processes × 3 Resources (Default)"]
        n = preset["processes"]
        m = preset["resources"]
        alloc_c = self.Matrix()
        max_c = self.Matrix()
        need_c = self.Matrix()

        for i in range(n):
            for j in range(m):
                alloc_c[i][j] = preset["allocation"][i][j]
                max_c[i][j] = preset["maximum"][i][j]

        ok = self.bankers_c.calculateNeed(n, m, alloc_c, max_c, need_c)
        self.assertEqual(ok, 1)

        expected_need = [
            [7, 4, 3],
            [1, 2, 2],
            [6, 0, 0],
            [0, 1, 1],
            [4, 3, 1]
        ]
        actual_need = [[need_c[i][j] for j in range(m)] for i in range(n)]
        self.assertEqual(actual_need, expected_need)

    def test_06_run_safety_algorithm(self):
        """6. Run the safety algorithm in C"""
        preset = self.PRESETS["5 Processes × 3 Resources (Default)"]
        n, m = preset["processes"], preset["resources"]
        alloc_c = self.Matrix()
        need_c = self.Matrix()
        avail_c = self.Vector()
        seq_c = self.Sequence()

        need_vals = [[7, 4, 3], [1, 2, 2], [6, 0, 0], [0, 1, 1], [4, 3, 1]]
        for i in range(n):
            for j in range(m):
                alloc_c[i][j] = preset["allocation"][i][j]
                need_c[i][j] = need_vals[i][j]

        avail_vals = [3, 3, 2]
        for j in range(m):
            avail_c[j] = avail_vals[j]

        result = self.bankers_c.safetyAlgorithm(n, m, alloc_c, need_c, avail_c, seq_c)
        self.assertEqual(result, 1)

    def test_07_verify_safe_sequence(self):
        """7. Verify the safe sequence is exactly P1 -> P3 -> P4 -> P0 -> P2"""
        preset = self.PRESETS["5 Processes × 3 Resources (Default)"]
        n, m = preset["processes"], preset["resources"]
        alloc_c = self.Matrix()
        need_c = self.Matrix()
        avail_c = self.Vector()
        seq_c = self.Sequence()

        need_vals = [[7, 4, 3], [1, 2, 2], [6, 0, 0], [0, 1, 1], [4, 3, 1]]
        for i in range(n):
            for j in range(m):
                alloc_c[i][j] = preset["allocation"][i][j]
                need_c[i][j] = need_vals[i][j]

        avail_vals = [3, 3, 2]
        for j in range(m):
            avail_c[j] = avail_vals[j]

        self.bankers_c.safetyAlgorithm(n, m, alloc_c, need_c, avail_c, seq_c)
        seq = [f"P{seq_c[i]}" for i in range(n)]
        self.assertEqual(seq, ["P1", "P3", "P4", "P0", "P2"])

    def test_08_submit_valid_resource_request(self):
        """8. Submit a valid resource request for P1 [1, 0, 2]"""
        preset = self.PRESETS["5 Processes × 3 Resources (Default)"]
        n, m = preset["processes"], preset["resources"]
        alloc_c = self.Matrix()
        need_c = self.Matrix()
        avail_c = self.Vector()
        req_c = self.Vector()

        need_vals = [[7, 4, 3], [1, 2, 2], [6, 0, 0], [0, 1, 1], [4, 3, 1]]
        for i in range(n):
            for j in range(m):
                alloc_c[i][j] = preset["allocation"][i][j]
                need_c[i][j] = need_vals[i][j]

        avail_vals = [3, 3, 2]
        for j in range(m):
            avail_c[j] = avail_vals[j]

        req_c[0] = 1; req_c[1] = 0; req_c[2] = 2

        # P1 request [1, 0, 2]
        granted = self.bankers_c.requestResources(1, n, m, req_c, alloc_c, need_c, avail_c)
        self.assertEqual(granted, 1)

        # Verify state modified correctly after grant
        self.assertEqual([avail_c[j] for j in range(m)], [2, 3, 0])
        self.assertEqual([alloc_c[1][j] for j in range(m)], [3, 0, 2])
        self.assertEqual([need_c[1][j] for j in range(m)], [0, 2, 0])

    def test_09_reject_request_exceeding_need(self):
        """9. Reject a request exceeding Need (e.g. P1 requests 2 of R0 where Need=1)"""
        preset = self.PRESETS["5 Processes × 3 Resources (Default)"]
        n, m = preset["processes"], preset["resources"]
        alloc_c = self.Matrix()
        need_c = self.Matrix()
        avail_c = self.Vector()
        req_c = self.Vector()

        need_vals = [[7, 4, 3], [1, 2, 2], [6, 0, 0], [0, 1, 1], [4, 3, 1]]
        for i in range(n):
            for j in range(m):
                alloc_c[i][j] = preset["allocation"][i][j]
                need_c[i][j] = need_vals[i][j]

        for j in range(m):
            avail_c[j] = 3

        req_c[0] = 2; req_c[1] = 0; req_c[2] = 0 # P1 Need[0] is 1, so 2 exceeds Need

        granted = self.bankers_c.requestResources(1, n, m, req_c, alloc_c, need_c, avail_c)
        self.assertEqual(granted, 0)
        # Verify state unchanged
        self.assertEqual([alloc_c[1][j] for j in range(m)], [2, 0, 0])

    def test_10_reject_request_exceeding_available(self):
        """10. Reject a request exceeding Available (e.g. P0 requests 4 of R0 where Avail=3)"""
        preset = self.PRESETS["5 Processes × 3 Resources (Default)"]
        n, m = preset["processes"], preset["resources"]
        alloc_c = self.Matrix()
        need_c = self.Matrix()
        avail_c = self.Vector()
        req_c = self.Vector()

        need_vals = [[7, 4, 3], [1, 2, 2], [6, 0, 0], [0, 1, 1], [4, 3, 1]]
        for i in range(n):
            for j in range(m):
                alloc_c[i][j] = preset["allocation"][i][j]
                need_c[i][j] = need_vals[i][j]

        avail_vals = [3, 3, 2]
        for j in range(m):
            avail_c[j] = avail_vals[j]

        req_c[0] = 4; req_c[1] = 0; req_c[2] = 0 # Exceeds Available[0] = 3

        granted = self.bankers_c.requestResources(0, n, m, req_c, alloc_c, need_c, avail_c)
        self.assertEqual(granted, 0)
        # Verify Available unchanged
        self.assertEqual([avail_c[j] for j in range(m)], [3, 3, 2])

    def test_11_reject_unsafe_request_and_verify_rollback(self):
        """11. Reject an unsafe request and verify rollback (e.g. P4 requests [3, 3, 0])"""
        preset = self.PRESETS["5 Processes × 3 Resources (Default)"]
        n, m = preset["processes"], preset["resources"]
        alloc_c = self.Matrix()
        need_c = self.Matrix()
        avail_c = self.Vector()
        req_c = self.Vector()

        need_vals = [[7, 4, 3], [1, 2, 2], [6, 0, 0], [0, 1, 1], [4, 3, 1]]
        for i in range(n):
            for j in range(m):
                alloc_c[i][j] = preset["allocation"][i][j]
                need_c[i][j] = need_vals[i][j]

        avail_vals = [3, 3, 2]
        for j in range(m):
            avail_c[j] = avail_vals[j]

        # P4 Need is [4, 3, 1], Available is [3, 3, 2].
        # Request [3, 3, 0] <= Need and <= Available, but leaves Available [0, 0, 2], which is UNSAFE.
        req_c[0] = 3; req_c[1] = 3; req_c[2] = 0

        granted = self.bankers_c.requestResources(4, n, m, req_c, alloc_c, need_c, avail_c)
        self.assertEqual(granted, 0) # Must be rejected due to unsafe state

        # Verify rollback in C: allocation, need, and available must be exactly restored
        self.assertEqual([alloc_c[4][j] for j in range(m)], [0, 0, 2])
        self.assertEqual([need_c[4][j] for j in range(m)], [4, 3, 1])
        self.assertEqual([avail_c[j] for j in range(m)], [3, 3, 2])

    def test_12_submit_valid_resource_release(self):
        """12. Submit a valid resource release for P1 releasing [1, 0, 0]"""
        preset = self.PRESETS["5 Processes × 3 Resources (Default)"]
        n, m = preset["processes"], preset["resources"]
        alloc_c = self.Matrix()
        need_c = self.Matrix()
        avail_c = self.Vector()
        rel_c = self.Vector()

        need_vals = [[7, 4, 3], [1, 2, 2], [6, 0, 0], [0, 1, 1], [4, 3, 1]]
        for i in range(n):
            for j in range(m):
                alloc_c[i][j] = preset["allocation"][i][j]
                need_c[i][j] = need_vals[i][j]

        avail_vals = [3, 3, 2]
        for j in range(m):
            avail_c[j] = avail_vals[j]

        rel_c[0] = 1; rel_c[1] = 0; rel_c[2] = 0 # P1 has [2, 0, 0]

        ok = self.bankers_c.releaseResources(1, m, rel_c, alloc_c, need_c, avail_c)
        self.assertEqual(ok, 1)

        # Verify state updated
        self.assertEqual([alloc_c[1][j] for j in range(m)], [1, 0, 0])
        self.assertEqual([avail_c[j] for j in range(m)], [4, 3, 2])
        self.assertEqual([need_c[1][j] for j in range(m)], [2, 2, 2])

    def test_13_reject_release_exceeding_allocation(self):
        """13. Reject a release exceeding allocation (e.g. P4 releasing [1, 0, 0] when allocation is [0, 0, 2])"""
        preset = self.PRESETS["5 Processes × 3 Resources (Default)"]
        n, m = preset["processes"], preset["resources"]
        alloc_c = self.Matrix()
        need_c = self.Matrix()
        avail_c = self.Vector()
        rel_c = self.Vector()

        for i in range(n):
            for j in range(m):
                alloc_c[i][j] = preset["allocation"][i][j]
                need_c[i][j] = 1

        for j in range(m):
            avail_c[j] = 3

        rel_c[0] = 1; rel_c[1] = 0; rel_c[2] = 0 # P4 holds 0 of R0

        ok = self.bankers_c.releaseResources(4, m, rel_c, alloc_c, need_c, avail_c)
        self.assertEqual(ok, 0)
        # Verify state unchanged
        self.assertEqual([alloc_c[4][j] for j in range(m)], [0, 0, 2])

    def test_14_verify_graph_and_matrices_update_after_operations(self):
        """14. Verify graph SVG and matrix dataframes dynamically reflect updated state"""
        total = [10, 5, 7]
        alloc = [
            [0, 1, 0],
            [3, 0, 2], # Granted request updated
            [3, 0, 2],
            [2, 1, 1],
            [0, 0, 2]
        ]
        avail = [2, 3, 0]

        svg = streamlit_app.generate_rag_svg(5, 3, alloc, total, avail, active_proc="P1")
        self.assertIn("<svg", svg)
        self.assertIn("P0", svg)
        self.assertIn("P4", svg)
        self.assertIn("R0", svg)
        self.assertIn("R2", svg)
        self.assertIn("Avail: 2", svg)
        self.assertIn("Avail: 3", svg)
        self.assertIn("Avail: 0", svg)
        # Check arrow markers
        self.assertIn('marker-end="url(#allocArrow)"', svg)
        self.assertIn('stroke="#2563EB"', svg) # Blue allocation edges

    def test_15_reinitialize_with_different_configuration(self):
        """15. Reinitialize system with 4 processes and 3 resources"""
        custom_alloc = [
            [1, 0, 1],
            [2, 1, 0],
            [0, 2, 1],
            [1, 1, 1]
        ]
        custom_max = [
            [2, 1, 2],
            [3, 2, 1],
            [1, 3, 2],
            [2, 2, 2]
        ]
        custom_tot = [6, 6, 5]
        n, m = 4, 3

        alloc_c = self.Matrix()
        max_c = self.Matrix()
        need_c = self.Matrix()
        avail_c = self.Vector()
        seq_c = self.Sequence()

        for i in range(n):
            for j in range(m):
                alloc_c[i][j] = custom_alloc[i][j]
                max_c[i][j] = custom_max[i][j]

        for j in range(m):
            used = sum(custom_alloc[i][j] for i in range(n))
            avail_c[j] = custom_tot[j] - used

        ok = self.bankers_c.calculateNeed(n, m, alloc_c, max_c, need_c)
        self.assertEqual(ok, 1)

        is_safe = self.bankers_c.safetyAlgorithm(n, m, alloc_c, need_c, avail_c, seq_c)
        self.assertEqual(is_safe, 1)
        seq = [f"P{seq_c[i]}" for i in range(n)]
        self.assertEqual(len(seq), 4)

        # Generate graph for custom 4x3
        svg = streamlit_app.generate_rag_svg(n, m, custom_alloc, custom_tot, [avail_c[j] for j in range(m)])
        self.assertIn("P3", svg)
        self.assertNotIn("P4", svg) # Only P0..P3
        self.assertIn("R2", svg)

if __name__ == "__main__":
    unittest.main()
