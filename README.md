# localcsp

An offline, stateful mock of an **Infoblox CSP** (Universal DDI) as-a-service API — a
"Moto-equivalent" for **NIOS-X as a Service**. It lets you drive the
deploy→read-back loop (create a Service Deployment, get back the Cloud Service IPs the POP
would mint) entirely offline, so downstream automation (e.g. an AWS edge that terminates
the IPsec tunnels) can be tested end-to-end without a real tenant or a real POP.

Born out of a project that fronts a NIOS-XaaS POP with an AWS edge to serve a public domain
authoritatively. The AWS side is testable offline with Moto; there is no Moto for Infoblox —
this fills that gap.

## Run it

```bash
uv run localcsp                      # serves on 127.0.0.1:8081
# or point your client at it:
export CSP_BASE_URL=http://127.0.0.1:8081
export CSP_API_KEY=anything-nonempty
```

```bash
uv run --extra dev pytest            # the deploy→read-back loop, auth, validation
```

## Two modes

**1. Stateful as-a-service loop (Python/FastAPI).** Models the deploy graph — **Service →
Capability → Service Deployment → Service Location** — and the consolidated create call that
mints the two **Cloud Service IPs** (public IKE peer endpoints, one per AZ), the values you
can't know until the POP exists. State is in-memory and resets per process. This is the path
the `uv run localcsp` / `pytest` commands above exercise. See
[`docs/api-model.md`](docs/api-model.md) for the object shapes it returns.

**2. Spec-driven full surface (Prism).** The entire BloxOne / Universal DDI API — DNS views,
auth zones, records, servers (`dnsconfig`), IPAM, DNS data, Threat Defense, anycast, keys, and
the rest — is mocked straight from the vendored OpenAPI specs in [`specs/`](specs/), so you can
hit *any* documented endpoint with schema-valid request/response behavior:

```bash
./scripts/mock-all.sh                 # one Prism mock per service, ports 4010-4022
# then, e.g. (Prism mounts each spec's paths at the root; any non-empty token satisfies auth):
curl -H "Authorization: Bearer x" http://127.0.0.1:4013/dns/view     # dnsconfig: DNS views
curl -H "Authorization: Bearer x" http://127.0.0.1:4018/ipam/subnet  # ipam: subnets
```

The specs are vendored unmodified from the public, Apache-2.0
[`infobloxopen/bloxone-go-client`](https://github.com/infobloxopen/bloxone-go-client) — the
same source the official Go client and `terraform-provider-bloxone` are generated from. See
[`specs/NOTICE.md`](specs/NOTICE.md) for the service→port→base-path map and attribution.

Auth (mode 1) mirrors the documented scheme: `Authorization: Token <api-key>` (any non-empty
token passes).

## Scope & non-goals

- **Behavior, not fidelity.** Provisioning is instant (real POPs sit in `not_ready` for
  minutes). Cloud Service IPs are minted from TEST-NET-2 (`198.51.100.0/24`) so they're
  visibly fake but public-shaped.
- **Not a security boundary.** Tokens aren't verified beyond non-emptiness.
- **Illustrative.** The FastAPI mode is a hand-written test double, not a spec; the Prism mode
  serves the upstream specs as-is. All addresses in tests and docs are example/documentation
  ranges.

## Roadmap

- [x] Full-surface schema mock via vendored OpenAPI specs + Prism.
- [ ] Make the stateful FastAPI mode stitch into the spec mocks (stateful DDI objects, not just
  schema-valid stubs).
- [ ] Status state machine (`not_ready → ready → connected`) on a timer for realism.
- [ ] A `refresh-specs` script to re-pull the vendored specs from upstream.
