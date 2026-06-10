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

## What it models

The as-a-service object graph described in the public documentation (Creating As-a-Service;
Configuring an IPSec Tunnel): **Service → Capability → Service Deployment → Service Location**.
The point of interest is the consolidated create call, which mints the two **Cloud Service
IPs** (the public IKE peer endpoints, one per AZ) — the values you can't know until the POP
exists. See [`docs/api-model.md`](docs/api-model.md) for the object shapes the mock returns.

Auth mirrors the documented scheme: `Authorization: Token <api-key>` (any non-empty token
passes). State is in-memory and resets per process, so every test session is clean.

## Scope & non-goals

- **Behavior, not fidelity.** Provisioning is instant (real POPs sit in `not_ready` for
  minutes). Cloud Service IPs are minted from TEST-NET-2 (`198.51.100.0/24`) so they're
  visibly fake but public-shaped.
- **Not a security boundary.** Tokens aren't verified beyond non-emptiness.
- **as-a-service surface only.** DDI data-plane objects (zones/records/views) are out of
  scope here — those are covered by the `bloxone` Terraform provider against a real tenant.
- **Illustrative.** Shapes and field names follow the public docs and ordinary API use; this
  is a local test double, not a spec. All addresses in tests and docs are example/documentation
  ranges.

## Roadmap

- [ ] Align routes to an OpenAPI spec drop + optional Prism mode for pure schema validation.
- [ ] Model Access Location / Connection objects (tunnel IDs, credential refs) more fully if
  automation needs them.
- [ ] Status state machine (`not_ready → ready → connected`) on a timer for realism.
