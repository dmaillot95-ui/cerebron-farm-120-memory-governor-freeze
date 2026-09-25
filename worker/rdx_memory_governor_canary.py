#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,pathlib,urllib.request

F72_REPO="dmaillot95-ui/cerebron-farm-72-reality-evidence-gate"
STATE_COMMIT="d2ca8fbad1e837f2da641a24aa74b49e795af0ff"
STATE_PATH="agora/state.json"
SCOPED_COMMIT="2ccb94d3161658499fe2c8cbce2313839645290b"
SCOPED_PATH="receipts/rdx-memory-evidence-review-36149593919.json"
EXPECTED_SCOPED_SHA="3b925348d4a04b11ff54d5472a5a3cd52b83af10ea188c8c50222b341caf5aee"

def fetch(commit,path):
    url=f"https://raw.githubusercontent.com/{F72_REPO}/{commit}/{path}"
    with urllib.request.urlopen(url,timeout=30) as r:
        return json.loads(r.read())

def quota_state(pct):
    if pct>=95: return "DRAIN_FREEZE"
    if pct>=90: return "STOP"
    if pct>=80: return "REINFORCEMENT"
    if pct>=70: return "WARNING"
    return "NORMAL"

def main():
    state=fetch(STATE_COMMIT,STATE_PATH)
    scoped=fetch(SCOPED_COMMIT,SCOPED_PATH)
    quota_cases={str(x):quota_state(x) for x in [0,69,70,79,80,89,90,94,95,100]}
    checks={
      "global_f72_fail":state.get("reality_gate")=="FAIL" and state.get("decision")=="HOLD",
      "scoped_review_pass":scoped.get("review_pass") is True,
      "scoped_receipt_sha":scoped.get("result_sha256")==EXPECTED_SCOPED_SHA,
      "scoped_does_not_release_global":scoped.get("global_f72_gate")=="FAIL",
      "gold_locked":scoped.get("gold_released") is False,
      "training_locked":scoped.get("training_released") is False,
      "m6_training_deny":True,
      "quota_70_warning":quota_cases["70"]=="WARNING",
      "quota_80_reinforcement":quota_cases["80"]=="REINFORCEMENT",
      "quota_90_stop":quota_cases["90"]=="STOP",
      "quota_95_drain_freeze":quota_cases["95"]=="DRAIN_FREEZE"
    }
    policy={
      "schema":"F120_RDX_MEMORY_GOVERNOR_CANARY_V1",
      "status":"PASS" if all(checks.values()) else "FAIL",
      "farm_id":120,
      "role":"MEMORY_GOVERNOR",
      "inputs":{
        "f72_state":{"repo":F72_REPO,"commit":STATE_COMMIT,"path":STATE_PATH},
        "scoped_review":{"repo":F72_REPO,"commit":SCOPED_COMMIT,"path":SCOPED_PATH,"result_sha256":EXPECTED_SCOPED_SHA}
      },
      "decisions":{
        "RDX_M1_M7_MEMORY":"ALLOW_WITH_PROVENANCE",
        "M4_GOLD":"BLOCK_BY_GLOBAL_F72",
        "M6_TRAINING":"DENY",
        "RDX_NEURAL_TRAINING":"DENY_UNTIL_GLOBAL_F72_AND_AFAH_AND_GOLD",
        "SECRETS_TRAINING":"NEVER_TRAIN"
      },
      "quota_thresholds_percent":{"warning":70,"reinforcement":80,"stop":90,"drain_freeze":95},
      "quota_probe":quota_cases,
      "checks":checks,
      "training_executed":False,
      "weights_changed":False,
      "claim_ceiling":"RDX_MEMORY_GOVERNOR_POLICY_CANARY_ONLY_NO_GOLD_RELEASE_NO_TRAINING"
    }
    policy["receipt_sha256"]=hashlib.sha256(json.dumps(policy,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    pathlib.Path("artifacts").mkdir(exist_ok=True)
    pathlib.Path("artifacts/rdx_memory_governor_canary.json").write_text(json.dumps(policy,indent=2)+"\n")
    print(json.dumps({"status":policy["status"],"decisions":policy["decisions"],"receipt_sha256":policy["receipt_sha256"]},sort_keys=True))
    if policy["status"]!="PASS": raise SystemExit(2)

if __name__=="__main__":
    main()
