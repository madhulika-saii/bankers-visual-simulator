import unittest
import json
import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:5000/api"

class TestDynamicBankersSimulator(unittest.TestCase):
    @classmethod
    def get(cls, endpoint):
        req = urllib.request.Request(f"{BASE_URL}{endpoint}")
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode())

    @classmethod
    def post(cls, endpoint, data):
        req = urllib.request.Request(
            f"{BASE_URL}{endpoint}",
            data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode())

    def test_1_configuration_3x2(self):
        """Test 3 processes and 2 resources configuration"""
        payload = {
            "processes": 3,
            "resources": 2,
            "total": [5, 5],
            "allocation": [[1, 1], [2, 1], [1, 2]],
            "maximum": [[2, 2], [2, 2], [3, 3]]
        }
        status, res = self.post("/initialize", payload)
        self.assertEqual(status, 200)
        state = res["state"]
        self.assertEqual(state["processes"], 3)
        self.assertEqual(state["resources"], 2)
        self.assertEqual(state["available"], [1, 1])

        # Test safety
        status, s_res = self.post("/safety", {})
        self.assertEqual(status, 200)
        self.assertTrue(s_res["safe"])
        self.assertEqual(len(s_res["safe_sequence"]), 3)

        # Test request grant
        status, req_res = self.post("/request", {"process": 1, "request": [0, 1]})
        self.assertEqual(status, 200)
        self.assertTrue(req_res["granted"])
        self.assertEqual(req_res["state"]["available"], [1, 0])

        # Test request reject exceeding need
        status, rej_res = self.post("/request", {"process": 1, "request": [1, 0]})
        self.assertEqual(status, 200)
        self.assertFalse(rej_res["granted"])
        self.assertEqual(rej_res["reason"], "exceeds_need")

        # Test release
        status, rel_res = self.post("/release", {"process": 1, "release": [1, 1]})
        self.assertEqual(status, 200)
        self.assertTrue(rel_res["released"])

    def test_2_configuration_5x3(self):
        """Test default 5 processes and 3 resources benchmark"""
        status, res = self.post("/initialize", {"preset": "5x3"})
        if status != 200:
            payload = {
                "processes": 5, "resources": 3, "total": [10, 5, 7],
                "allocation": [[0, 1, 0], [2, 0, 0], [3, 0, 2], [2, 1, 1], [0, 0, 2]],
                "maximum": [[7, 5, 3], [3, 2, 2], [9, 0, 2], [2, 2, 2], [4, 3, 3]]
            }
            status, res = self.post("/initialize", payload)
        self.assertEqual(status, 200)
        self.assertEqual(res["state"]["processes"], 5)
        self.assertEqual(res["state"]["resources"], 3)

        # Safety check
        status, s_res = self.post("/safety", {})
        self.assertEqual(status, 200)
        self.assertTrue(s_res["safe"])
        self.assertEqual(s_res["safe_sequence"], ["P1", "P3", "P4", "P0", "P2"])

        # Test request P1 [1, 0, 2]
        status, req_res = self.post("/request", {"process": 1, "request": [1, 0, 2]})
        self.assertEqual(status, 200)
        self.assertTrue(req_res["granted"])

    def test_3_configuration_6x4(self):
        """Test 6 processes and 4 resources configuration"""
        status, res = self.post("/initialize", {"preset": "6x4"})
        self.assertEqual(status, 200)
        state = res["state"]
        self.assertEqual(state["processes"], 6)
        self.assertEqual(state["resources"], 4)
        self.assertEqual(len(state["available"]), 4)

        # Safety check
        status, s_res = self.post("/safety", {})
        self.assertEqual(status, 200)
        self.assertTrue(s_res["safe"])
        self.assertEqual(len(s_res["safe_sequence"]), 6)

        # Valid Request
        status, req_res = self.post("/request", {"process": 0, "request": [1, 0, 0, 0]})
        self.assertEqual(status, 200)
        self.assertTrue(req_res["granted"])

        # Request exceeding Available
        status, rej_res = self.post("/request", {"process": 0, "request": [9, 9, 9, 9]})
        self.assertEqual(status, 200)
        self.assertFalse(rej_res["granted"])

    def test_4_buffer_overflow_prevention(self):
        """Test that invalid dimensions exceeding MAX_P=10, MAX_R=10 are rejected"""
        status, res = self.post("/initialize", {"processes": 12, "resources": 3})
        self.assertEqual(status, 400)
        self.assertIn("Invalid dimensions", res["error"])

        status, res = self.post("/initialize", {"processes": 4, "resources": 15})
        self.assertEqual(status, 400)
        self.assertIn("Invalid dimensions", res["error"])

if __name__ == "__main__":
    unittest.main()
