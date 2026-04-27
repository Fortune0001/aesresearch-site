#!/usr/bin/env bash
# Wire defensive-grab domains to redirect to the canonical aesresearch.ai.
#
# For each domain:
#   1. Add proxied A record @ → 192.0.2.1 (RFC 5737 placeholder; Cloudflare proxies before DNS resolves)
#   2. Add proxied CNAME www → apex
#   3. Replace the http_request_dynamic_redirect entrypoint with one rule:
#      true → 301 redirect to https://aesresearch.ai${http.request.uri.path} (preserve query string)
#   4. Add TXT _dmarc → v=DMARC1; p=reject; rua=mailto:postmaster@aesresearch.ai
#      (parked domain hardening — never sends mail, anyone forging gets rejected)
#   5. Add TXT @ → v=spf1 -all (no servers authorized to send from this domain)
#
# Token requirements: Zone:DNS:Edit + Zone:Single Redirect:Edit on the listed zones.
# Reads CLOUDFLARE_API_TOKEN_DNS from ~/.keys.env.

set -euo pipefail

TOKEN=$(grep "^CLOUDFLARE_API_TOKEN_DNS=" ~/.keys.env | cut -d= -f2-)
if [ -z "$TOKEN" ]; then
  echo "ERROR: CLOUDFLARE_API_TOKEN_DNS not found in ~/.keys.env" >&2
  exit 1
fi

CANONICAL="aesresearch.ai"

# zone_id:domain pairs
ZONES=(
  "392c8782cba217a1aa649e6fdb269ceb:appliedemergentsciences.com"
  "d1b58afa123b3c674254e9e9b04a6cf0:aesresearch.org"
  "d8ae767060202a07b1114b8cce4fa131:aes-research.com"
)

api() {
  local method=$1 path=$2 body=${3:-}
  local args=(-sS -X "$method" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json")
  [ -n "$body" ] && args+=(-d "$body")
  curl "${args[@]}" "https://api.cloudflare.com/client/v4$path"
}

check() {
  local label=$1 resp=$2
  if echo "$resp" | python -c "import sys, json; sys.exit(0 if json.load(sys.stdin)['success'] else 1)" 2>/dev/null; then
    echo "  ✓ $label"
  else
    echo "  ✗ $label"
    echo "$resp" | python -m json.tool >&2 || echo "$resp" >&2
    return 1
  fi
}

for entry in "${ZONES[@]}"; do
  ZONE_ID=${entry%%:*}
  DOMAIN=${entry##*:}
  echo "=== $DOMAIN ($ZONE_ID) ==="

  # 1. A @ → 192.0.2.1 proxied
  resp=$(api POST "/zones/$ZONE_ID/dns_records" "$(python -c "
import json
print(json.dumps({'type':'A','name':'$DOMAIN','content':'192.0.2.1','proxied':True,'ttl':1,'comment':'redirect-only placeholder; traffic terminated at Cloudflare proxy before DNS resolves'}))
")")
  check "A @ → 192.0.2.1 (proxied)" "$resp" || true

  # 2. CNAME www → apex proxied
  resp=$(api POST "/zones/$ZONE_ID/dns_records" "$(python -c "
import json
print(json.dumps({'type':'CNAME','name':'www','content':'$DOMAIN','proxied':True,'ttl':1}))
")")
  check "CNAME www → @ (proxied)" "$resp" || true

  # 3. Single Redirect rule (replace entrypoint of http_request_dynamic_redirect phase)
  redirect_body=$(python -c "
import json
print(json.dumps({
  'rules': [{
    'expression': 'true',
    'action': 'redirect',
    'description': 'Canonical redirect to $CANONICAL',
    'action_parameters': {
      'from_value': {
        'status_code': 301,
        'target_url': {
          'expression': 'concat(\"https://$CANONICAL\", http.request.uri.path)'
        },
        'preserve_query_string': True
      }
    }
  }]
}))
")
  resp=$(api PUT "/zones/$ZONE_ID/rulesets/phases/http_request_dynamic_redirect/entrypoint" "$redirect_body")
  check "Single Redirect → https://$CANONICAL" "$resp" || true

  # 4. TXT _dmarc → reject
  resp=$(api POST "/zones/$ZONE_ID/dns_records" "$(python -c "
import json
print(json.dumps({'type':'TXT','name':'_dmarc','content':'v=DMARC1; p=reject; rua=mailto:postmaster@aesresearch.ai','ttl':1}))
")")
  check "TXT _dmarc (p=reject)" "$resp" || true

  # 5. TXT @ → SPF -all
  resp=$(api POST "/zones/$ZONE_ID/dns_records" "$(python -c "
import json
print(json.dumps({'type':'TXT','name':'$DOMAIN','content':'v=spf1 -all','ttl':1}))
")")
  check "TXT @ (SPF -all)" "$resp" || true

  echo ""
done

echo "Done. Verify with:"
echo "  curl -I https://appliedemergentsciences.com"
echo "  curl -I https://aesresearch.org"
echo "  curl -I https://aes-research.com"
