#!/usr/bin/env bash
set -u

WATCH_PID="${1:?usage: monitor_onestepfold_rsync.sh PID}"
SOURCE_ROOT="/hpc2hdd/home/shuang886/Folding/"
DEST_ROOT="pc@DiamondHill:/media/PM982/onestepfold/"
LOG_PATH="/hpc2hdd/home/shuang886/Folding/rsync_onestepfold.log"

log() {
  printf '[%s] %s\n' "$(date --iso-8601=seconds)" "$*" >>"$LOG_PATH"
}

log "tmux watcher started for rsync pid=${WATCH_PID}"
while kill -0 "$WATCH_PID" 2>/dev/null; do
  sleep 30
done

log "initial rsync exited; starting resumable verification pass"
rsync -a --partial --append-verify --human-readable --info=progress2 --stats \
  -e 'ssh -o BatchMode=yes -o ConnectTimeout=10' \
  "$SOURCE_ROOT" "$DEST_ROOT" >>"$LOG_PATH" 2>&1
status=$?
log "final rsync exit=${status}"
exit "$status"
