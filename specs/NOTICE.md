# Vendored OpenAPI specs

The `specs/<service>/openapi.yaml` files are vendored **unmodified** from the public,
Apache-2.0-licensed [`infobloxopen/bloxone-go-client`](https://github.com/infobloxopen/bloxone-go-client)
repository (`<service>/api/openapi.yaml`), which is the source the official BloxOne Go client
and the `terraform-provider-bloxone` are generated from. They describe the BloxOne / Universal
DDI ("CSP") API surface.

They are included here so localcsp can serve the **full API surface** as a schema-driven mock
(see the root `README.md`, "Spec-driven mode"). No spec was edited; refresh them by re-pulling
from upstream.

Upstream license: Apache License 2.0 — see
<https://github.com/infobloxopen/bloxone-go-client/blob/master/LICENSE>.

## Services and base paths

| Service | Base path | What it covers |
|---|---|---|
| anycast | /api/anycast/v1 | Anycast config |
| clouddiscovery | /api/cloud_discovery/v2 | Cloud discovery |
| dfp | /api/atcdfp/v1 | DNS Forwarding Proxy |
| dnsconfig | /api/ddi/v1 | DNS views, auth zones, records, servers |
| dnsdata | /api/ddi/v1 | DNS data-plane |
| fw | /api/atcfw/v1 | Threat Defense / firewall |
| inframgmt | /api/infra/v1 | Infrastructure (hosts, services) |
| infraprovision | /host-activation/v1 | Host activation |
| ipam | /api/ddi/v1 | IPAM (address blocks, subnets, ranges) |
| ipamfederation | /api/ddi/v1 | IPAM federation |
| keys | /api/ddi/v1 | DNSSEC / TSIG keys |
| redirect | /api/atcfw/v1 | Redirect config |
| upgradepolicy | /api/upgrade_policy | Software/config update scheduling |
