"""
docs/paper2/data/fullember3_supervisor.py — babysitter for the s3.67 sweep 3.

A single plain detached OS process (nohup'd; survives SSH/session death) that
runs the four phase x topology cells in sequence via fullember3.py, watches
worker JSONL growth for stalls, kills+resumes on stall or crash, and writes
the morning report.

Launch:
  cd /data/max/ember
  nohup .venv/bin/python docs/paper2/data/fullember3_supervisor.py \
      > /data/max/fullember3/supervisor.log 2>&1 < /dev/null &
  disown

Status:  cat /data/max/fullember3/status.json
Smoke:   ... fullember3_supervisor.py --smoke   (2 smoke cells, then report)
"""
import argparse
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

REPO = Path("/data/max/ember")
STATE_DIR = Path("/data/max/fullember3")
STAGING = Path("/data/max/ember-qc-data/ember-qc/runs_unfinished")
RUNNER = REPO / "docs/paper2/data/fullember3.py"
PYTHON = str(REPO / ".venv/bin/python")
STATUS = STATE_DIR / "status.json"
PHASE_RESULTS = STATE_DIR / "phase_results.jsonl"

POLL_S = 60           # stall-poll cadence
STALL_S = 30 * 60     # no JSONL byte growth for this long => kill + resume
MAX_RETRIES = 4       # per phase; then compile-what-exists and move on
EXIT_CHECKPOINTED = 3

PHASES = [
    ("phaseA", "pegasus_16", 100),
    ("phaseA", "zephyr_12", 100),
    ("phaseB", "pegasus_16", 64),
    ("phaseB", "zephyr_12", 64),
]
SMOKE_PHASES = [
    ("smoke", "pegasus_16", 100),
    ("smoke", "zephyr_12", 100),
]

CHILD_ENV = dict(os.environ,
                 OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1",
                 MKL_NUM_THREADS="1", PYTHONUNBUFFERED="1")


def log(msg: str) -> None:
    print(f"[{datetime.now().isoformat(timespec='seconds')}] {msg}", flush=True)


def jsonl_bytes(batch_dir: Path) -> int:
    total = 0
    for f in batch_dir.glob("workers/*.jsonl"):
        try:
            total += f.stat().st_size
        except OSError:
            pass
    return total


def jsonl_lines(batch_dir: Path) -> int:
    total = 0
    for f in batch_dir.glob("workers/*.jsonl"):
        try:
            with open(f, "rb") as fh:
                total += fh.read().count(b"\n")
        except OSError:
            pass
    return total


def write_status(**kw) -> None:
    kw["updated"] = datetime.now().isoformat(timespec="seconds")
    tmp = STATUS.with_suffix(".tmp")
    tmp.write_text(json.dumps(kw, indent=2))
    tmp.replace(STATUS)


def newest_batch(after: float):
    cands = [d for d in STAGING.glob("batch_*") if d.stat().st_mtime >= after - 5]
    return max(cands, key=lambda d: d.stat().st_mtime) if cands else None


def kill_tree(proc: subprocess.Popen) -> None:
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    for _ in range(20):
        if proc.poll() is not None:
            break
        time.sleep(1)
    if proc.poll() is None:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait()


def run_phase(phase: str, topo: str, workers: int, history: list) -> dict:
    """Run one phase cell to completion (with stall-kill + resume retries).
    Returns a summary dict for the report."""
    label = f"{phase}/{topo}"
    batch_id = None       # set once the batch dir is known; used for --resume
    planned = None
    retries = 0

    while True:
        cmd = [PYTHON, str(RUNNER), phase, topo, "--workers", str(workers)]
        if batch_id:
            cmd += ["--resume", batch_id]
        launch_t = time.time()
        child_log = STATE_DIR / f"runner_{phase}_{topo}.log"
        log(f"{label}: launching (retry {retries}/{MAX_RETRIES}) "
            f"{'resume ' + batch_id if batch_id else 'fresh'}")
        with open(child_log, "a") as lf:
            lf.write(f"\n===== launch {datetime.now().isoformat()} "
                     f"retry={retries} resume={batch_id} =====\n")
            lf.flush()
            proc = subprocess.Popen(
                cmd, cwd=str(REPO), env=CHILD_ENV,
                stdout=lf, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL, start_new_session=True,
            )

            # Discover the batch dir (fresh launches only)
            batch_dir = STAGING / batch_id if batch_id else None
            last_bytes = -1
            last_growth = time.time()
            stalled = False
            while proc.poll() is None:
                time.sleep(POLL_S)
                if batch_dir is None or not batch_dir.exists():
                    nb = newest_batch(launch_t)
                    if nb is not None:
                        batch_dir = nb
                        batch_id = nb.name
                        try:
                            cfg = json.loads((nb / "config.json").read_text())
                            planned = cfg.get("total_measured_runs")
                        except OSError:
                            pass
                        log(f"{label}: batch {batch_id} planned={planned}")
                cur = jsonl_bytes(batch_dir) if batch_dir else 0
                if cur != last_bytes:
                    last_bytes = cur
                    last_growth = time.time()
                lines = jsonl_lines(batch_dir) if batch_dir else 0
                write_status(state="running", phase=label, batch=batch_id,
                             planned=planned, done_lines=lines,
                             retries=retries,
                             stalled_for_s=int(time.time() - last_growth),
                             history=history)
                if time.time() - last_growth > STALL_S:
                    log(f"{label}: STALL — no JSONL growth for "
                        f"{int(time.time() - last_growth)}s; killing tree")
                    stalled = True
                    kill_tree(proc)
                    break

        rc = proc.returncode
        if rc == 0 and not stalled:
            lines = jsonl_lines(batch_dir) if batch_dir and batch_dir.exists() else None
            log(f"{label}: COMPLETE (planned={planned})")
            return {"phase": label, "state": "complete", "batch": batch_id,
                    "planned": planned, "retries": retries}
        if rc == EXIT_CHECKPOINTED or stalled or rc != 0:
            retries += 1
            why = "stall" if stalled else f"exit={rc}"
            history.append(f"{label}: retry {retries} ({why})")
            log(f"{label}: incomplete ({why}); "
                f"{'resuming' if retries <= MAX_RETRIES else 'RETRY CAP HIT'}")
            if retries > MAX_RETRIES:
                # Compile what exists so the partial data is still usable.
                state = "incomplete"
                if batch_dir and batch_dir.exists():
                    try:
                        from ember_qc.compile import compile_batch
                        compile_batch(batch_dir)
                        state = "incomplete-compiled"
                    except Exception as e:  # keep the supervisor alive
                        log(f"{label}: compile_batch failed: {e}")
                return {"phase": label, "state": state, "batch": batch_id,
                        "planned": planned, "retries": retries,
                        "resume_cmd": (f"{PYTHON} {RUNNER} {phase} {topo} "
                                       f"--workers {workers} --resume {batch_id}")}
            if batch_id is None:
                log(f"{label}: no batch dir ever appeared; relaunching fresh")
            time.sleep(10)


def write_report(results: list, history: list, t0: float) -> None:
    lines = ["# Full-Ember sweep 3 — run report",
             f"Generated {datetime.now().isoformat(timespec='seconds')}; "
             f"total wall {int((time.time() - t0) / 60)} min.", ""]
    finals = {}
    if PHASE_RESULTS.exists():
        for ln in PHASE_RESULTS.read_text().splitlines():
            try:
                r = json.loads(ln)
                finals[(r["phase"], r["topology"])] = r["final_dir"]
            except (json.JSONDecodeError, KeyError):
                pass
    lines.append("| phase | state | batch | planned | retries | final dir |")
    lines.append("|---|---|---|---|---|---|")
    for r in results:
        ph, topo = r["phase"].split("/")
        fd = finals.get((ph, topo), "-")
        lines.append(f"| {r['phase']} | {r['state']} | {r.get('batch')} "
                     f"| {r.get('planned')} | {r.get('retries')} | {fd} |")
    if history:
        lines += ["", "## Restart history"] + [f"- {h}" for h in history]
    incomplete = [r for r in results if r["state"] != "complete"]
    if incomplete:
        lines += ["", "## Incomplete phases — resume commands"]
        for r in incomplete:
            if r.get("resume_cmd"):
                lines += [f"- `{r['resume_cmd']}`"]
    # Analysis over whatever completed
    final_dirs = [finals[k] for k in finals]
    if final_dirs:
        lines += ["", "## Analysis", "```"]
        try:
            out = subprocess.run(
                [PYTHON, str(REPO / "docs/paper2/data/analyze_fullember3.py")]
                + final_dirs,
                cwd=str(REPO), env=CHILD_ENV, capture_output=True, text=True,
                timeout=1800)
            lines += (out.stdout or "").splitlines()
            if out.returncode != 0:
                lines += ["[analyzer stderr]"] + (out.stderr or "").splitlines()[-30:]
        except Exception as e:
            lines += [f"analyzer failed: {e}"]
        lines += ["```"]
    (STATE_DIR / "REPORT.md").write_text("\n".join(lines) + "\n")
    log(f"report written: {STATE_DIR / 'REPORT.md'}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    phases = SMOKE_PHASES if args.smoke else PHASES

    t0 = time.time()
    history: list = []
    results: list = []
    log(f"supervisor start: {len(phases)} phases, pid {os.getpid()}")
    for phase, topo, workers in phases:
        try:
            results.append(run_phase(phase, topo, workers, history))
        except Exception as e:
            import traceback
            log(f"{phase}/{topo}: SUPERVISOR ERROR {e}\n{traceback.format_exc()}")
            results.append({"phase": f"{phase}/{topo}", "state": f"error: {e}",
                            "batch": None, "planned": None, "retries": None})
        write_status(state="between-phases", done=[r["phase"] for r in results],
                     history=history)
    write_report(results, history, t0)
    ok = all(r["state"] == "complete" for r in results)
    write_status(state="finished" if ok else "finished-with-incomplete",
                 results=results, history=history)
    log(f"supervisor done: {'ALL COMPLETE' if ok else 'SOME INCOMPLETE'}")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
