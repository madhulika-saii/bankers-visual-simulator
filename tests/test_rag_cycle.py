import os
import sys
import unittest
import ctypes

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))
sys.path.insert(0, PROJECT_ROOT)

class TestRAGCycleDetection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        lib_path = os.path.join(PROJECT_ROOT, "backend", "libbankers.so")
        cls.lib = ctypes.CDLL(lib_path)
        cls.MAX_P = 10
        cls.MAX_R = 10
        cls.Matrix = (ctypes.c_int * cls.MAX_R) * cls.MAX_P
        cls.CyclePath = ctypes.c_int * (cls.MAX_P * 2 + 2)

        cls.lib.detectRAGCycle.argtypes = [
            ctypes.c_int, ctypes.c_int,
            cls.Matrix, cls.Matrix,
            cls.CyclePath, ctypes.POINTER(ctypes.c_int)
        ]
        cls.lib.detectRAGCycle.restype = ctypes.c_int

    def test_single_instance_deadlock_cycle(self):
        """Test classic 2x2 single-instance deadlock cycle: P0 -> R1 -> P1 -> R0 -> P0"""
        alloc = self.Matrix()
        req = self.Matrix()

        # P0 holds R0, requests R1
        alloc[0][0] = 1
        req[0][1] = 1

        # P1 holds R1, requests R0
        alloc[1][1] = 1
        req[1][0] = 1

        c_path = self.CyclePath()
        c_len = ctypes.c_int(0)
        has_cycle = self.lib.detectRAGCycle(2, 2, alloc, req, c_path, ctypes.byref(c_len))

        self.assertEqual(has_cycle, 1, "Cycle must be detected in 2x2 deadlock")
        self.assertGreater(c_len.value, 2)
        raw_path = [c_path[i] for i in range(c_len.value)]
        labels = [f"P{v}" if v < 2 else f"R{v - 2}" for v in raw_path]
        cycle_str = " -> ".join(labels)
        print("Detected Cycle:", cycle_str)

        # Path must start and end at the same node
        self.assertEqual(labels[0], labels[-1], "Cycle path must be closed loop")
        # Must contain P0, P1, R0, R1
        self.assertIn("P0", labels)
        self.assertIn("P1", labels)
        self.assertIn("R0", labels)
        self.assertIn("R1", labels)

    def test_single_instance_acyclic_safe(self):
        """Test 3x3 single-instance acyclic graph: P0 holds R0, requests R1; P1 holds R1, requests R2; P2 requests R2"""
        alloc = self.Matrix()
        req = self.Matrix()

        # P0 holds R0, requests R1
        alloc[0][0] = 1
        req[0][1] = 1

        # P1 holds R1, requests R2
        alloc[1][1] = 1
        req[1][2] = 1

        # P2 holds nothing, requests R2
        req[2][2] = 1

        c_path = self.CyclePath()
        c_len = ctypes.c_int(0)
        has_cycle = self.lib.detectRAGCycle(3, 3, alloc, req, c_path, ctypes.byref(c_len))

        self.assertEqual(has_cycle, 0, "Graph is acyclic, no cycle should be detected")
        self.assertEqual(c_len.value, 0)

    def test_3_node_deadlock_cycle(self):
        """Test 3-process 3-resource cycle: P0 -> R1 -> P1 -> R2 -> P2 -> R0 -> P0"""
        alloc = self.Matrix()
        req = self.Matrix()

        alloc[0][0] = 1; req[0][1] = 1 # P0 holds R0, requests R1
        alloc[1][1] = 1; req[1][2] = 1 # P1 holds R1, requests R2
        alloc[2][2] = 1; req[2][0] = 1 # P2 holds R2, requests R0

        c_path = self.CyclePath()
        c_len = ctypes.c_int(0)
        has_cycle = self.lib.detectRAGCycle(3, 3, alloc, req, c_path, ctypes.byref(c_len))

        self.assertEqual(has_cycle, 1, "Cycle must be detected in 3x3 loop")
        self.assertGreater(c_len.value, 3)
        raw_path = [c_path[i] for i in range(c_len.value)]
        labels = [f"P{v}" if v < 3 else f"R{v - 3}" for v in raw_path]
        self.assertEqual(labels[0], labels[-1])
        print("Detected 3-node Cycle:", " -> ".join(labels))

if __name__ == "__main__":
    unittest.main()
