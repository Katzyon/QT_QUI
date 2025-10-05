
#!/usr/bin/env python3
"""
show_pickle.py — inspect pickle files safely(ish) and readably.

Usage:
  python show_pickle.py /path/to/file_or_dir [--head 20] [--full]
  python show_pickle.py "D:\DATA\Patterns\479\Culture\culture_2025-09-16_12-09.pkl" --head 20 --full

Notes:
- Only open pickle files you trust.
- If the pickle contains custom classes whose modules aren't available,
  we fall back to "stub" classes so you can still see their attributes.
"""

from __future__ import annotations
import argparse
import pickle
import pprint
from pathlib import Path
import sys
import types
from datetime import datetime

def _mk_stub(module_name: str, class_name: str):
    """Create a minimal placeholder class for (module_name, class_name)."""
    mod = sys.modules.get(module_name)
    if mod is None:
        mod = types.ModuleType(module_name)
        sys.modules[module_name] = mod
    if not hasattr(mod, class_name):
        # minimal new-style class; default __setstate__/__getstate__ via __dict__
        cls = type(class_name, (object,), {})
        setattr(mod, class_name, cls)
    return getattr(mod, class_name)

class FallbackUnpickler(pickle.Unpickler):
    """Unpickler that can map unknown (module, name) to stub classes."""
    def __init__(self, file, stub_map=None):
        super().__init__(file)
        self.stub_map = stub_map or {}

    def find_class(self, module, name):
        key = (module, name)
        if key in self.stub_map:
            return self.stub_map[key]
        try:
            return super().find_class(module, name)
        except Exception:
            # last-resort: create a stub on the fly
            return _mk_stub(module, name)

def try_load_pickle(path: Path):
    """Try normal pickle.load first; on failure, retry with fallback stubs."""
    with path.open("rb") as f:
        try:
            return pickle.load(f)
        except Exception as e:
            # Common custom types you may expect; add more as needed:
            stub_map = {
                ("Protocol", "Stage"): _mk_stub("Protocol", "Stage"),
                ("protocolSet", "ProtocolSet"): _mk_stub("protocolSet", "ProtocolSet"),
            }
            f.seek(0)
            return FallbackUnpickler(f, stub_map=stub_map).load()

def is_probably_sequence_pickle(obj) -> bool:
    return isinstance(obj, dict) and {"index", "protocol_number", "sequence"}.issubset(obj.keys())

def _preview(seq, head: int):
    seq = list(seq)
    n = min(len(seq), head)
    return {"length": len(seq), "head": seq[:n]}

def describe_object(obj, head: int, full: bool):
    """Return a human-friendly dict summary for printing."""
    try:
        if is_probably_sequence_pickle(obj):
            # Looks like a {index, protocol_number, sequence, start_time}
            out = {
                "type": "sequence_dict",
                "index": obj.get("index"),
                "protocol_number": obj.get("protocol_number"),
                "start_time": _ts(obj.get("start_time")),
                "sequence": _preview(obj.get("sequence", []), head),
            }
            return out

        # Generic containers
        if isinstance(obj, (list, tuple, set)):
            return {"type": type(obj).__name__, "length": len(obj),
                    "preview": list(obj)[:head]}

        if isinstance(obj, dict):
            keys = list(obj.keys())
            sample = {k: obj[k] for k in keys[:min(len(keys), head)]}
            return {"type": "dict", "keys_count": len(keys), "sample": sample}

        # Try to introspect a custom object with __dict__
        d = getattr(obj, "__dict__", None)
        if isinstance(d, dict):
            out = {"type": f"{obj.__class__.__module__}.{obj.__class__.__name__}",
                   "attrs_count": len(d)}
            # Smart summary for common names if present
            if "stages" in d and isinstance(d["stages"], (list, tuple)):
                out["stages_count"] = len(d["stages"])
                out["stages_preview"] = [
                    summarize_stage(s, head=head) for s in d["stages"][:min(len(d["stages"]), 5)]
                ]
            # Also include a small attribute sample
            keys = list(d.keys())
            out["attr_sample"] = {k: _brief(d[k], head) for k in keys[:min(len(keys), 12)]}
            if full:
                out["all_attrs"] = {k: _brief(v, head) for k, v in d.items()}
            return out

        # Fallback: repr
        return {"type": type(obj).__name__, "repr": repr(obj)}
    except Exception as e:
        return {"error": f"Failed to describe object: {e}", "type": type(obj).__name__}

def summarize_stage(stage_obj, head: int = 20):
    """Heuristic summarizer for a 'Stage'-like object (works with stubs)."""
    d = getattr(stage_obj, "__dict__", {}) or {}
    out = {"type": f"{stage_obj.__class__.__module__}.{stage_obj.__class__.__name__}"}
    fields = [
        "number", "stim_type", "groups_number", "group_size", "number_cells",
        "groups_period", "on_time", "stim_time", "sequence_repeats",
        "is_manual", "is_probability_stim", "recording"
    ]
    for k in fields:
        if k in d:
            out[k] = d[k]
    if "sequence" in d:
        out["sequence"] = _preview(d["sequence"], head)
    if "output_group" in d:
        out["output_group_size"] = len(d.get("output_group") or [])
    if "groups" in d and isinstance(d["groups"], (list, tuple)):
        out["groups_count"] = len(d["groups"])
        # show first few groups (by size)
        sample = []
        for g in d["groups"][:min(len(d["groups"]), 5)]:
            if isinstance(g, dict) and "cells" in g:
                sample.append({"cells_len": len(g["cells"]), "color": g.get("color")})
            else:
                sample.append(_brief(g, head))
        out["groups_preview"] = sample
    return out

def _brief(x, head: int):
    """Compact representation for nested values."""
    if isinstance(x, (list, tuple, set)):
        return {"type": type(x).__name__, "len": len(x), "head": list(x)[:min(len(x), head)]}
    if isinstance(x, dict):
        keys = list(x.keys())
        return {"type": "dict", "keys": len(keys),
                "sample": {k: x[k] for k in keys[:min(len(keys), 5)]}}
    if isinstance(x, (str, int, float, bool)) or x is None:
        return x
    # object-ish
    name = f"{x.__class__.__module__}.{x.__class__.__name__}"
    d = getattr(x, "__dict__", None)
    if isinstance(d, dict):
        return {"type": name, "attrs": list(d.keys())[:min(len(d), 8)]}
    return {"type": name}

def _ts(t):
    try:
        return datetime.fromtimestamp(float(t)).isoformat(timespec="seconds")
    except Exception:
        return t

def print_report(path: Path, head: int, full: bool):
    obj = try_load_pickle(path)
    print(f"\n=== {path.name} ===")
    summary = describe_object(obj, head=head, full=full)
    pprint.pp(summary, sort_dicts=False)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", type=Path, help="Pickle file OR directory containing *.pkl files")
    ap.add_argument("--head", type=int, default=20, help="Preview length for sequences/lists")
    ap.add_argument("--full", action="store_true", help="Print all object attributes (verbose)")
    args = ap.parse_args()

    p = args.path
    if p.is_dir():
        pkls = sorted(p.glob("*.pkl"))
        if not pkls:
            print(f"No .pkl files in {p}")
            sys.exit(1)
        for f in pkls:
            print_report(f, head=args.head, full=args.full)
    elif p.is_file():
        print_report(p, head=args.head, full=args.full)
    else:
        print(f"Not found: {p}")
        sys.exit(1)

if __name__ == "__main__":
    main()
