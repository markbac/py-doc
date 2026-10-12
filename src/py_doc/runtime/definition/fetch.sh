#!/bin/sh
# usage: fetch.sh NAME DESTINATION
# Download NAME as tools.lock describes it, and stop unless the checksum matches the recorded one.
set -eu
line=$(awk -v n="$1" '$1 == n { print $3 " " $4 }' /tmp/build/tools.lock)
[ -n "$line" ] || { echo "$1 is not in tools.lock" >&2; exit 1; }
url=${line% *}
sum=${line#* }
[ "$sum" != "-" ] || { echo "No checksum is recorded for $1. Run: py-doc tools lock" >&2; exit 1; }
curl -fsSL "$url" -o "$2"
echo "$sum  $2" | sha256sum -c -
