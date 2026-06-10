#!/usr/bin/env bash
# Serve every vendored OpenAPI spec as a Prism mock, one process per service.
# Each spec gets its own port (Prism mocks a single document per instance).
# Requires Node; uses npx to fetch @stoplight/prism-cli on first run.
#
#   ./scripts/mock-all.sh            # foreground; Ctrl-C stops all
#
# Then hit e.g.  curl http://127.0.0.1:4013/api/ddi/v1/dns/view   (dnsconfig)
set -euo pipefail
cd "$(dirname "$0")/.."

HOST="${LOCALCSP_MOCK_HOST:-127.0.0.1}"
PRISM="npx -y @stoplight/prism-cli@5 mock --dynamic -h $HOST"

# service:port map (alphabetical, 4010+)
SERVICES=(
  "anycast:4010" "clouddiscovery:4011" "dfp:4012" "dnsconfig:4013"
  "dnsdata:4014" "fw:4015" "inframgmt:4016" "infraprovision:4017"
  "ipam:4018" "ipamfederation:4019" "keys:4020" "redirect:4021"
  "upgradepolicy:4022"
)

pids=()
cleanup() { echo; echo "stopping mocks..."; kill "${pids[@]}" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

echo "starting Prism mocks (host $HOST):"
for entry in "${SERVICES[@]}"; do
  svc="${entry%%:*}"; port="${entry##*:}"
  spec="specs/$svc/openapi.yaml"
  [ -f "$spec" ] || { echo "  skip $svc (no spec)"; continue; }
  $PRISM "$spec" -p "$port" >"/tmp/prism-$svc.log" 2>&1 &
  pids+=("$!")
  printf "  %-16s -> http://%s:%s\n" "$svc" "$HOST" "$port"
done

echo "logs in /tmp/prism-<service>.log ; Ctrl-C to stop."
wait
