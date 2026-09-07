#!/bin/bash
cd /data/max/ember
.venv/bin/python docs/paper2/data/rewrite_board.py new new+mm > docs/paper2/data/rewrite_board_new2.log 2>&1
.venv/bin/python docs/paper2/data/rewrite_board.py summary > docs/paper2/data/rewrite_board_summary2.log 2>&1
.venv/bin/python docs/paper2/data/invariance_probe.py > docs/paper2/data/invariance_probe.log 2>&1
echo done-all2 >> docs/paper2/data/rewrite_board_summary2.log
