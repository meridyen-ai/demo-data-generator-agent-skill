"""Merge the agent-authored instructions into the scaffold -> final snapshot.json.

instructions.json (authored by the agent) shape:
{
  "global": "=== CONNECTION INSTRUCTIONS ===\\n[ENRICHMENT ONLY] ... [/SQL GEN]",
  "tables": { "public.sales_orders": "METRIC: ...\\nDIMENSIONS: ...", ... },
  "hidden_overrides": { "public.sales_orders": { "channel": false, "order_no": true } },
  "deselect_tables": [ "public.some_table" ],
  "prompts": [ "What was net revenue in 2026?", "Top 5 customers by revenue" ]
}
All keys optional except "global" and "tables".
"""
from __future__ import annotations


def assemble(draft: dict, instr: dict) -> dict:
    snap = dict(draft)
    ss = snap["selected_schema"]

    global_text = instr.get("global", "").strip()
    snap["instructions"] = global_text
    ss["_connection_meta"]["instructions"] = global_text

    for key, text in (instr.get("tables") or {}).items():
        if key in ss:
            ss[key]["instructions"] = text.strip()

    for key, overrides in (instr.get("hidden_overrides") or {}).items():
        if key not in ss:
            continue
        for col, hidden in overrides.items():
            if col not in ss[key]["columns"]:
                continue
            if hidden:
                ss[key]["columns"][col]["is_hidden"] = True
            else:
                ss[key]["columns"][col].pop("is_hidden", None)

    for key in (instr.get("deselect_tables") or []):
        if key in ss:
            ss[key]["selected"] = False

    prompts = instr.get("prompts") or []
    snap["prompts_data"] = [{"prompt": p} if isinstance(p, str) else p for p in prompts]

    return snap
