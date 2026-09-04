#!/bin/bash
# s3.127 paired board, in sequence so the wall-based arms do not compete
# with the harness or with each other more than necessary.
cd /data/max/ember
until grep -qE 'done-fingerprint|Traceback' docs/paper2/data/plane_fingerprint_step5.log; do sleep 20; done
.venv/bin/python docs/paper2/data/rewrite_board.py new new+mm mm > docs/paper2/data/rewrite_board_new.log 2>&1
PYTHONPATH=/data/max/ember-archive/packages/ember-qc/src .venv/bin/python docs/paper2/data/rewrite_board.py old > docs/paper2/data/rewrite_board_old.log 2>&1
.venv/bin/python docs/paper2/data/rewrite_board.py summary > docs/paper2/data/rewrite_board_summary.log 2>&1
echo done-all >> docs/paper2/data/rewrite_board_summary.log
