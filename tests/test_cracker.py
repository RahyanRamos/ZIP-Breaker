from __future__ import annotations

import unittest

from zip_breaker.control import CrackControl
from zip_breaker.cracker import ZipPasswordCracker
from zip_breaker.models import CrackStatus


class FakeTester:
    def __init__(self, expected: str) -> None:
        self.expected = expected
        self.received: list[str] = []

    def test(self, candidate: str) -> bool:
        self.received.append(candidate)
        return candidate == self.expected


class CrackerTests(unittest.TestCase):
    def test_stops_when_password_is_found(self) -> None:
        tester = FakeTester("correta")
        updates = []
        cracker = ZipPasswordCracker(
            "ignored.zip", progress_interval=1, tester=tester
        )

        result = cracker.crack(
            ["errada", "correta", "nem testada"], total=3, on_progress=updates.append
        )

        self.assertEqual(result.status, CrackStatus.FOUND)
        self.assertEqual(result.password, "correta")
        self.assertEqual(result.attempts, 2)
        self.assertEqual(tester.received, ["errada", "correta"])
        self.assertEqual(updates[-1].attempts, 2)

    def test_reports_not_found(self) -> None:
        cracker = ZipPasswordCracker(
            "ignored.zip", tester=FakeTester("ausente")
        )
        result = cracker.crack(["a", "b"], total=2)
        self.assertEqual(result.status, CrackStatus.NOT_FOUND)
        self.assertEqual(result.attempts, 2)

    def test_honors_preexisting_cancellation(self) -> None:
        tester = FakeTester("senha")
        control = CrackControl()
        control.cancel()
        cracker = ZipPasswordCracker("ignored.zip", tester=tester)

        result = cracker.crack(["senha"], control=control)

        self.assertEqual(result.status, CrackStatus.CANCELLED)
        self.assertEqual(result.attempts, 0)
        self.assertEqual(tester.received, [])

    def test_invalid_progress_interval_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            ZipPasswordCracker(
                "ignored.zip", progress_interval=0, tester=FakeTester("x")
            )


if __name__ == "__main__":
    unittest.main()
