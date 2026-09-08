#!/usr/bin/env bash
set -euo pipefail

MODEL="${1:-}"
MODE="${2:-run}"
WORK="${DS1000_WORKDIR:-/data/projects/deep-analyze-lab/artifacts/phase3/official-eval/DS-1000}"
VENV="/data/venvs/ds1000-eval"
AUDIT="/data/projects/deep-analyze-lab/labs/phase-03-evaluation/scripts/audit_ds1000_answers.py"
if [[ -z "$MODEL" ]]; then
  echo "usage: $0 MODEL [run|probe]" >&2
  exit 2
fi

mkdir -p "$WORK/results"
python3 "$AUDIT" --answers "$WORK/data/${MODEL}-answers.jsonl" > "$WORK/results/${MODEL}-audit.json"
cat "$WORK/results/${MODEL}-audit.json"
SCRATCH="$(mktemp -d "${DS1000_SCRATCH_ROOT:-/tmp}/ds1000-eval.XXXXXX")"
cleanup() {
  rm -rf "$SCRATCH"
}
trap cleanup EXIT
cp -a "$WORK/." "$SCRATCH/work"
mkdir -p "$SCRATCH/venv" "$SCRATCH/root"

unshare --user --map-root-user --mount --fork --net bash -s -- "$SCRATCH" "$VENV" "$MODEL" "$MODE" <<'INNER'
set -euo pipefail
SCRATCH="$1"
SOURCE_VENV="$2"
MODEL="$3"
MODE="$4"
mount --make-rprivate /
mount --bind "$SOURCE_VENV" "$SCRATCH/venv"
mount -t tmpfs -o size=64m tmpfs "$SCRATCH/root"
mount -t tmpfs -o size=64m tmpfs /data
for sensitive_dir in /root /home /run/secrets /var/run/secrets; do
  if [[ -d "$sensitive_dir" ]]; then
    mount -t tmpfs -o size=4m tmpfs "$sensitive_dir"
  fi
done
export HOME="$SCRATCH/root"
export TMPDIR="$SCRATCH/tmp"
mkdir -p "$TMPDIR"
if [[ "$MODE" == "probe" ]]; then
  test ! -e /data/projects
  test ! -e "$HOME/.ssh"
  env -i HOME="$HOME" TMPDIR="$TMPDIR" PATH="/usr/bin:/bin"     "$SCRATCH/venv/bin/python" - <<'PY'
import os
import socket
import tensorflow as tf
assert "PHASE3_SECRET_CANARY" not in os.environ
assert not os.path.exists("/data/projects")
assert not os.path.exists("/root/.ssh")
assert not os.path.exists("/var/run/secrets/kubernetes.io/serviceaccount")
assert os.path.exists("/proc/self/exe")
assert int(tf.reduce_sum(tf.constant([2, 3])).numpy()) == 5
sock = socket.socket()
try:
    sock.connect(("1.1.1.1", 53))
except OSError:
    pass
else:
    raise AssertionError("network namespace unexpectedly connected")
print("DS1000_SANDBOX_PROBE_OK PROC_VISIBLE_USER_APPROVED")
PY
  exit 0
fi
cd "$SCRATCH/work"
env -i HOME="$HOME" TMPDIR="$TMPDIR" PATH="/usr/bin:/bin"   CUDA_VISIBLE_DEVICES="-1" TF_CPP_MIN_LOG_LEVEL="3"   "$SCRATCH/venv/bin/python" test_ds1000.py --model "$MODEL"
INNER

if [[ "$MODE" == "run" ]]; then
  mkdir -p "$WORK/results"
  cp "$SCRATCH/work/results/${MODEL}-result.txt" "$WORK/results/"
  cp "$SCRATCH/work/results/${MODEL}-log.json" "$WORK/results/"
fi
