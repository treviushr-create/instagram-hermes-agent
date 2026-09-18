#!/usr/bin/env bash
# Spin up a dedicated agent instance for one new customer.
#
# The honest reason this script exists: a small shop owner will never run
# `docker compose up`. The self-hosted README is for developers. For anyone
# else, Trevius runs the agent on their behalf — one Plow line, one deployed
# instance, per customer — and this script is the repeatable, non-manual way
# to do that instead of retyping the same six commands by hand each time a
# new customer signs up.
#
# What this does NOT do: onboard the customer's Instagram account itself
# (that's a human conversation — helping them switch to a professional
# account, add Trevius as an Instagram Tester or guiding App Review, and
# getting their access token). This script starts once you already have
# their INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_BUSINESS_ACCOUNT_ID in hand.
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
Usage: onboard_customer.sh <customer-name> <instagram-access-token> <instagram-business-account-id>

Example:
  ./scripts/onboard_customer.sh "loja-da-maria" "IGAA...xyz" "17841400000000000"

Requires: plow-agents on PATH, logged in (plow-agents login), and this
repo's image already pushed to ghcr.io/treviushr-create/instagram-hermes-agent.
EOF
  exit 1
}

[ $# -eq 3 ] || usage

customer_name="$1"
access_token="$2"
account_id="$3"
image_digest="${IMAGE_DIGEST:?set IMAGE_DIGEST to the pinned ghcr.io/...@sha256:... to deploy}"

echo "==> Onboarding: $customer_name"

echo "==> Finding a free Plow line..."
free_line="$(plow-agents lines | awk '$4 == "free" {print $1; exit}')"
if [ -z "$free_line" ]; then
  echo "No free line available -- every provisioned line is already assigned to a customer." >&2
  echo "This is a real capacity limit, not a bug: check with Plow about getting more lines" >&2
  echo "before onboarding more customers than you have lines for." >&2
  exit 1
fi
echo "    -> $free_line"

work_dir="$(mktemp -d)"
trap 'rm -rf "$work_dir"' EXIT
cp -r "$(dirname "$0")/.." "$work_dir/agent"
cd "$work_dir/agent"

echo "==> Writing $customer_name's credentials (not committed anywhere)..."
cat > .env <<EOF
INSTAGRAM_ACCESS_TOKEN=$access_token
INSTAGRAM_BUSINESS_ACCOUNT_ID=$account_id
EOF

echo "==> Requesting the deploy on $free_line..."
plow-agents deploy "$image_digest" --line "$free_line"

number="$(plow-agents lines | awk -v l="$free_line" '$1 == l {print $3}')"
echo "==> Done. $customer_name's agent number: $number"
echo "    Text that number to activate it, then give it to the customer."
echo "    Record this pairing somewhere durable (this script does not) —"
echo "    customer name, line id, and account id, so a future revoke/rotate"
echo "    knows which line belongs to whom."
