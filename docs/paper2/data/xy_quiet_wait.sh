#!/bin/bash
# s3.121 follow-up: the xy board was load-contaminated (74-116) and the
# decider cells never reached the move. Wait for a quiet box (1-min
# load < 30), then re-run the identical board once into
# xy_probe_quiet.{py,csv,log}. Launch:
#   nohup bash docs/paper2/data/xy_quiet_wait.sh \
#     > docs/paper2/data/xy_quiet_wait.log 2>&1 &
cd "$(dirname "$0")/../../.." || exit 1
echo "waiting for load < 30 (checking every 10 min); started $(date)"
while :; do
    load=$(cut -d' ' -f1 /proc/loadavg | cut -d. -f1)
    if [ "$load" -lt 30 ]; then break; fi
    echo "$(date '+%H:%M') load $load — waiting"
    sleep 600
done
echo "quiet at $(date), load $(cat /proc/loadavg); launching"
sed 's/xy_probe\.csv/xy_probe_quiet.csv/' \
    docs/paper2/data/xy_probe.py > docs/paper2/data/xy_probe_quiet.py
.venv/bin/python docs/paper2/data/xy_probe_quiet.py \
    > docs/paper2/data/xy_probe_quiet.log 2>&1
echo "done at $(date); sentinel + summary in xy_probe_quiet.log"
