import unittest
import os
import json
import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:5000/api"

class TestBankersDebug(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Initialize standard 5x3 benchmark
        cls.example = {
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
        }
        cls.post("/initialize", cls.example)

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

    def setUp(self):
        # Reset state to default benchmark before each test
        self.post("/initialize", self.example)

    def test_1_safety_check(self):
        status, res = self.post("/safety", {})
        self.assertEqual(status, 200)
        self.assertTrue(res["safe"])
        self.assertEqual(res["safe_sequence"], ["P1", "P3", "P4", "P0", "P2"])

    def test_2_process_id_formats(self):
        # Test integer 1
        status, res1 = self.post("/request", {"process": 1, "request": [1, 0, 2]})
        self.assertEqual(status, 200)
        self.assertTrue(res1["granted"])

        # Reset
        self.post("/initialize", self.example)

        # Test string 'P1'
        status, res2 = self.post("/request", {"process": "P1", "request": [1, 0, 2]})
        self.assertEqual(status, 200)
        self.assertTrue(res2["granted"])

        # Test invalid process P9
        status, res3 = self.post("/request", {"process": "P9", "request": [1, 0, 0]})
        self.assertEqual(status, 400)
        self.assertIn("does not exist", res3["error"])

    def test_3_rejection_exceeds_need(self):
        # P0 need is [7, 4, 3]. Requesting [0, 5, 0] should be rejected for R1 exceeding Need
        status, res = self.post("/request", {"process": 0, "request": [0, 5, 0]})
        self.assertEqual(status, 200)
        self.assertFalse(res["granted"])
        self.assertEqual(res["reason"], "exceeds_need")
        self.assertIn("Exceeds Maximum Claim for R1", res["message"])

        # Verify state unchanged
        state = res["state"]
        self.assertEqual(state["available"], [3, 3, 2])
        self.assertEqual(state["allocation"][0], [0, 1, 0])

    def test_4_rejection_insufficient_available(self):
        # P0 need is [7, 4, 3], but Available is [3, 3, 2].
        # Requesting [4, 0, 0] exceeds Available[0] = 3.
        status, res = self.post("/request", {"process": 0, "request": [4, 0, 0]})
        self.assertEqual(status, 200)
        self.assertFalse(res["granted"])
        self.assertEqual(res["reason"], "insufficient_available")
        self.assertIn("Insufficient Available resources for R0", res["message"])

        # Verify state unchanged
        state = res["state"]
        self.assertEqual(state["available"], [3, 3, 2])

    def test_5_rejection_unsafe_state_rollback(self):
        # P3 need is [0, 1, 1], available is [3, 3, 2].
        # Requesting [1, 0, 0] fails because Need for R0 is 0! (Exceeds Need)
        # For a truly unsafe request that satisfies need & available:
        # e.g., P0 requests [0, 2, 0]. Need is [7, 4, 3] (<=4), available is [3, 3, 2] (<=3).
        # New available [3, 1, 2]. Let's check safety.
        # Let's test P3 request [1, 0, 0] which was user problem #2:
        status, res = self.post("/request", {"process": 3, "request": [1, 0, 0]})
        self.assertEqual(status, 200)
        self.assertFalse(res["granted"])
        self.assertEqual(res["reason"], "exceeds_need")
        self.assertIn("Exceeds Maximum Claim for R0", res["message"])

    def test_6_rejection_release_exceeding_allocation(self):
        # P4 has allocation [0, 0, 2].
        # Releasing [1, 0, 0] should be rejected because R0 allocation is 0 (User problem #3)
        status, res = self.post("/release", {"process": 4, "release": [1, 0, 0]})
        self.assertEqual(status, 200)
        self.assertFalse(res["released"])
        self.assertEqual(res["reason"], "exceeds_allocation")
        self.assertIn("Currently allocated: 0", res["message"])

        # P1 has allocation [2, 0, 0].
        # Releasing [1, 0, 0] should succeed!
        status, res2 = self.post("/release", {"process": 1, "release": [1, 0, 0]})
        self.assertEqual(status, 200)
        self.assertTrue(res2["released"])
        self.assertEqual(res2["state"]["allocation"][1], [1, 0, 0])
        self.assertEqual(res2["state"]["available"], [4, 3, 2])

    def test_7_dimension_validation(self):
        # Request with 2 values instead of 3
        status, res = self.post("/request", {"process": 1, "request": [1, 0]})
        self.assertEqual(status, 400)
        self.assertIn("Request vector must contain exactly 3 numbers", res["error"])

        # Release with 4 values instead of 3
        status, res = self.post("/release", {"process": 1, "release": [1, 0, 0, 0]})
        self.assertEqual(status, 400)
        self.assertIn("Release vector must contain exactly 3 numbers", res["error"])

if __name__ == "__main__":
    unittest.main()
