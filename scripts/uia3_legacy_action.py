"""Dispatch an element's MSAA default action through UIA3 LegacyIAccessiblePattern.

The Codex in-app browser does not expose BOSS web content through
AccessibleObjectFromWindow, so direct oleacc MSAA tree matching cannot find
BOSS cards. UIA3 does expose the card, and its LegacyIAccessible pattern bridges
to the same MSAA default action without moving the mouse.
"""
import argparse
import json
import sys
from pathlib import Path

VENDOR = Path(__file__).resolve().parent / "_vendor"
if VENDOR.is_dir():
    sys.path.insert(0, str(VENDOR))

import comtypes  # noqa: E402
import comtypes.client  # noqa: E402
import comtypes.gen.UIAutomationClient as U  # noqa: E402

LEGACY_PATTERN_ID = 10018
MAX_NODES = 6000


def find_element(uia, hwnd, runtime_id):
    root = uia.ElementFromHandle(hwnd)
    elements = root.FindAll(4, uia.CreateTrueCondition())
    if elements.Length > MAX_NODES:
        raise ValueError("uia3_tree_exceeds_bound")
    target = tuple(runtime_id)
    for index in range(elements.Length):
        node = elements.GetElement(index)
        try:
            if tuple(node.GetRuntimeId()) == target:
                return node
        except Exception:
            continue
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--hwnd", type=int, required=True)
    parser.add_argument("--runtime-id", required=True)
    args = parser.parse_args()
    try:
        runtime_id = [int(value) for value in args.runtime_id.split(",")]
        uia = comtypes.client.CreateObject(U.CUIAutomation, interface=U.IUIAutomation)
        node = find_element(uia, args.hwnd, runtime_id)
        if node is None:
            print(json.dumps({"state": "unavailable", "reason": "element_not_found"}, ensure_ascii=False))
            return
        pointer = node.GetCurrentPattern(LEGACY_PATTERN_ID)
        legacy = pointer.QueryInterface(U.IUIAutomationLegacyIAccessiblePattern) if pointer else None
        action = legacy.CurrentDefaultAction if legacy else ""
        if not action:
            print(json.dumps({"state": "unavailable", "reason": "legacy_default_action_missing"}, ensure_ascii=False))
            return
        legacy.DoDefaultAction()
        print(json.dumps({"state": "dispatched", "transport": "uia3_legacy",
                          "default_action": action}, ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"state": "error", "reason": str(exc)[:300]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
