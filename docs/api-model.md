# API model

The object shapes localcsp implements, with example/documentation-range values throughout.
This is a local test double of the as-a-service surface; field names follow the public docs
and ordinary API use. Real provisioning is async and slower — the mock is instant.

## Object model

**Service → Capability → Service Deployment (endpoint) → Access Location → Location.**

### Service — `GET /api/universalinfra/v1/universalservices`

```jsonc
{ "id": "infra/universal_service/<token>", "name": "example-xaas",
  "ophid": "managedhost<token>",
  "capabilities": [ { "type": "dns", "service_status": "Available" } ] }
```

### Service Deployment (POP) — `GET /api/universalinfra/v1/endpoints`

```jsonc
{ "id": "infra/endpoint/<token>", "name": "example-xaas-sd",
  "service_location": "AWS US East (N. Virginia)",
  "service_ip": "192.0.2.10",                       // private DNS listener (/32)
  "cnames": ["198.51.100.4", "198.51.100.5"],       // the two Cloud Service IPs (IKE peers)
  "neighbour_ips": ["192.0.2.11", "192.0.2.12"],    // Primary / Secondary Source IPs
  "size": "S", "routing_type": "static", "preferred_provider": "Any",
  "universal_service_id": "<service token>" }
```

### Access Location — `GET /api/universalinfra/v1/accesslocations`

Fields: `id, name, endpoint_id, universal_service_id, location_id, identity,
identity_type, routing_type, type, tunnel_configs, status`.

## Envelopes

- List: `{"results": [ ... ]}`.
- Single by token: `{"result": { ... }}`.

## Field notes

- The **Cloud Service IPs** live in `cnames`.
- The **Source IPs** live in `neighbour_ips` (a single array: primary, secondary).
- The deployment object is `endpoint`; the service is `universal_service`; the deployment
  links back via `universal_service_id` (the bare token, not the full `infra/...` id).

## Create path

A single consolidated call rather than per-collection POSTs:

**`POST /api/universalinfra/v1/consolidated/configure`** with sub-objects that cross-link via
`ref_*` placeholder ids resolved server-side:

```jsonc
{
  "universal_service": { "operation": "CREATE", "name": "...", "capabilities": [{"type":"dns"}] },
  "endpoints":   { "create": [ { "id":"ref_ep", "name", "size", "service_location",
                                 "service_ip", "neighbour_ips":[src1,src2], "routing_type" } ] },
  "access_locations": { "create": [ { "endpoint_id":"ref_ep", "id":"ref_al", "location_id":"ref_loc",
                                 "type":"Site", "name", "tunnel_configs":[ {"name","physical_tunnels":[
                                    {"path":"primary","credential_id":"ref_cred","index":0},
                                    {"path":"secondary","credential_id":"ref_cred","index":1} ]} ] } ] },
  "credentials": { "create": [ {"id":"ref_cred","type":"psk","name","value":"<secret>"} ] },
  "locations": { "create": [ {"id":"ref_loc","name","address":{...}} ] }
}
```

The minted Cloud Service IPs are **not** in the create response — the endpoint provisions
async. Read them back with a separate `GET /api/universalinfra/v1/endpoints/{id}` →
`result.cnames`.

## Validation the mock enforces

Modeled so automation hits the same shape it would against a real POP:

1. **Access location `location_id` is required**, and the referenced Location must carry an
   address with a `country`.
2. **Minimum 2 physical tunnels** per access location, belonging to **one** `tunnel_config`
   (one edge device, two tunnels to the two cloud AZs) — not two single-tunnel connections.
3. **Identities are server-minted KeyIDs.** On create you omit identity; the response fills
   each physical tunnel with a KeyID `identity` and `remote_id: "infoblox.cloud"`, with
   `identity_type: "KeyID"`. A self-managed strongSwan edge uses that KeyID as its local id
   and `infoblox.cloud` as the remote id.
4. **`credential_id` can be reused** across both physical tunnels (one PSK, both legs).

## Auth

`Authorization: Token <api-key>` — any non-empty token passes in the mock. The PSK value in a
`credentials.create` entry is accepted but never stored or echoed back.
