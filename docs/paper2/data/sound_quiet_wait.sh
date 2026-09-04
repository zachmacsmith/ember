#!/bin/bash
# s3.124: the sound-plane board (11 arms, ~640 jobs) must run on a quiet
# box — the s3.113 load-collapse lesson. Wait for 1-min load < 30
# (checking every 10 min), then run sound_probe.py once.
#   nohup bash docs/paper2/data/sound_quiet_wait.sh \
#     > docs/paper2/data/sound_quiet_wait.log 2>&1 &
cd "$(dirname "$0")/../../.." || exit 1
echo "waiting for load < 30 (every 10 min); started $(date)"
while :; do
    load=$(cut -d' ' -f1 /proc/loadavg | cut -d. -f1)
    if [ "$load" -lt 30 ]; then break; fi
    echo "$(date '+%m-%d %H:%M') load $load — waiting"
    sleep 600
done
echo "quiet at $(date), load $(cat /proc/loadavg); launching"
.venv/bin/python docs/paper2/data/sound_probe.py \
    > docs/paper2/data/sound_probe.log 2>&1
echo "done at $(date); summary + sentinel in sound_probe.log"
