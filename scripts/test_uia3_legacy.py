import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import uia3_legacy_action as legacy_action


class FakeLegacy:
    def __init__(self, action):
        self.CurrentDefaultAction = action
        self.calls = 0

    def DoDefaultAction(self):
        self.calls += 1


class FakePointer:
    def __init__(self, legacy):
        self.legacy = legacy

    def QueryInterface(self, _interface):
        return self.legacy


class FakeNode:
    def __init__(self, runtime_id, legacy):
        self.runtime_id = runtime_id
        self.legacy = legacy

    def GetRuntimeId(self):
        return self.runtime_id

    def GetCurrentPattern(self, ident):
        if ident != legacy_action.LEGACY_PATTERN_ID:
            return None
        return FakePointer(self.legacy) if self.legacy else None


class FakeArray:
    def __init__(self, nodes):
        self.nodes = nodes
        self.Length = len(nodes)

    def GetElement(self, index):
        return self.nodes[index]


class FakeRoot:
    def __init__(self, nodes):
        self.nodes = nodes

    def FindAll(self, _scope, _condition):
        return FakeArray(self.nodes)


class FakeUIA:
    def __init__(self, nodes):
        self.nodes = nodes

    def ElementFromHandle(self, _hwnd):
        return FakeRoot(self.nodes)

    def CreateTrueCondition(self):
        return None


def dispatch(runtime_id, legacy, node_id=None):
    node = FakeNode(node_id or runtime_id, legacy)
    output = io.StringIO()
    with patch.object(legacy_action.comtypes.client, "CreateObject", return_value=FakeUIA([node])), \
            patch.object(sys, "argv", ["uia3", "--hwnd", "1",
                                       "--runtime-id", ",".join(map(str, runtime_id))]), \
            redirect_stdout(output):
        legacy_action.main()
    return json.loads(output.getvalue().strip().splitlines()[-1])


class Uia3LegacyTests(unittest.TestCase):
    def test_unique_default_action_is_dispatched_once(self):
        legacy = FakeLegacy("点击")
        result = dispatch([42, 1, 2, 3], legacy)
        self.assertEqual(result["state"], "dispatched")
        self.assertEqual(result["transport"], "uia3_legacy")
        self.assertEqual(legacy.calls, 1)

    def test_missing_default_action_does_not_dispatch(self):
        legacy = FakeLegacy("")
        result = dispatch([42, 1, 2, 3], legacy)
        self.assertEqual(result["state"], "unavailable")
        self.assertEqual(legacy.calls, 0)

    def test_missing_element_does_not_dispatch(self):
        legacy = FakeLegacy("点击")
        result = dispatch([42, 1, 2, 3], legacy, node_id=[42, 9, 9, 9])
        self.assertEqual(result["state"], "unavailable")
        self.assertEqual(legacy.calls, 0)


if __name__ == "__main__":
    unittest.main()
