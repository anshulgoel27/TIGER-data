#!/bin/bash
set -e;
export LC_ALL=en_US.UTF-8;

# ensure lftp exists and is executable
if [[ ! -f /usr/bin/lftp || ! -x /usr/bin/lftp ]]; then
  echo "lftp not installed on system";
  exit 1;
fi

# sync files from FTP server
lftp <<-SCRIPT
  open ftp2.census.gov
  mirror -e -n -r --parallel=20 --ignore-time /geo/tiger/TIGER2024/EDGES/ .
  exit
SCRIPT
