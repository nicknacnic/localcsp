"""localcsp — offline, stateful mock of an Infoblox CSP NIOS-X as a Service API.

Models the as-a-service surface from the public docs. The create is a single consolidated
call:

  POST /api/universalinfra/v1/consolidated/configure
       body: { universal_service, endpoints, access_locations, credentials, locations }
       sub-objects cross-link via ref_* placeholder IDs before real IDs exist.

Read-back:
  GET /api/universalinfra/v1/universalservices       -> {"results":[...]}
  GET /api/universalinfra/v1/endpoints  (and /{tok}) -> {"result":{... "cnames":[ip,ip] ...}}

`cnames` = the two Cloud Service IPs (public IKE peers) minted at provisioning.
`neighbour_ips` on an endpoint = the Primary/Secondary Source IPs.
Auth: `Authorization: Token <key>` (any non-empty); we model only the API-key path.

See docs/api-model.md for the object shapes and the validation this mock enforces.
"""
from __future__ import annotations

import ipaddress
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException

from .models import Capability, Endpoint, UniversalService

app = FastAPI(title="localcsp", description="Offline Infoblox CSP NIOS-XaaS mock")

_services: dict[str, UniversalService] = {}
_endpoints: dict[str, Endpoint] = {}
_access_locations: dict[str, dict] = {}
_credentials: dict[str, dict] = {}

# Cloud Service IPs (cnames) minted from TEST-NET-2 so they're visibly fake but public-shaped.
_cname_pool = (str(ip) for ip in ipaddress.ip_network("198.51.100.0/24").hosts())


def _tok() -> str:
    return uuid4().hex[:32]


def _require_token(authorization: str | None) -> None:
    if not authorization or not authorization.lower().startswith("token "):
        raise HTTPException(status_code=401, detail="missing 'Authorization: Token <key>'")
    if not authorization.split(" ", 1)[1].strip():
        raise HTTPException(status_code=401, detail="empty API token")


# ---- Create: the consolidated configure call (the real write path) ----

@app.post("/api/universalinfra/v1/consolidated/configure", status_code=201)
def configure(payload: dict, authorization: str | None = Header(default=None)):
    """Create service + endpoints + access locations + credentials in one shot.

    Resolves ref_* placeholder ids, mints cnames per endpoint, and stores objects so the
    GET read-backs return them (the deploy → read-cnames two-step).
    """
    _require_token(authorization)
    refmap: dict[str, str] = {}  # ref_* -> real token

    us = payload.get("universal_service") or {}
    if us.get("operation", "CREATE").upper() != "CREATE":
        raise HTTPException(status_code=422, detail="only operation=CREATE is modeled")
    svc_tok = _tok()
    svc = UniversalService(
        id=f"infra/universal_service/{svc_tok}",
        ophid=f"managedhost{svc_tok[:20]}",
        name=us.get("name", "unnamed"),
        capabilities=[Capability(**c) for c in us.get("capabilities", [{"type": "dns"}])],
    )
    _services[svc_tok] = svc

    for cred in (payload.get("credentials", {}) or {}).get("create", []):
        ctok = _tok()
        refmap[cred.get("id", ctok)] = ctok
        _credentials[ctok] = {k: v for k, v in cred.items() if k != "value"}  # never store PSK

    # Locations first, so access_locations can resolve location_id ref_* references.
    for loc in (payload.get("locations", {}) or {}).get("create", []):
        if not (loc.get("address") or {}).get("country"):
            raise HTTPException(status_code=500, detail="error fetching country from location address")
        refmap[loc.get("id", _tok())] = f"infra/location/{_tok()}"

    created_endpoints = []
    for ep in (payload.get("endpoints", {}) or {}).get("create", []):
        nbrs = ep.get("neighbour_ips", [])
        if len(nbrs) != 2:
            raise HTTPException(status_code=422, detail="endpoint.neighbour_ips must be [primary, secondary]")
        etok = _tok()
        refmap[ep.get("id", etok)] = etok
        endpoint = Endpoint(
            id=f"infra/endpoint/{etok}",
            name=ep.get("name", "ep"),
            universal_service_id=svc_tok,
            service_location=ep["service_location"],
            service_ip=ep["service_ip"],
            neighbour_ips=nbrs,
            size=ep.get("size", "S"),
            routing_type=ep.get("routing_type", "static"),
            preferred_provider=ep.get("preferred_provider", "Any"),
            routing_config=ep.get("routing_config", {}),
            cnames=[next(_cname_pool), next(_cname_pool)],  # the two Cloud Service IPs
        )
        _endpoints[etok] = endpoint
        created_endpoints.append(endpoint)

    created_als = []
    for al in (payload.get("access_locations", {}) or {}).get("create", []):
        # Validation modeled from the documented constraints (see docs/api-model.md):
        if not al.get("location_id"):
            raise HTTPException(status_code=400, detail="access location location_id cannot be empty")
        phys = [t for tc in al.get("tunnel_configs", []) for t in tc.get("physical_tunnels", [])]
        if len(phys) < 2:
            raise HTTPException(status_code=400, detail="minimum of 2 physical tunnels are required")
        atok = _tok()
        resolved = dict(al)
        resolved["endpoint_id"] = refmap.get(al.get("endpoint_id"), al.get("endpoint_id"))
        resolved["location_id"] = refmap.get(al["location_id"], al["location_id"])
        resolved["id"] = f"infra/access_location/{atok}"
        resolved["universal_service_id"] = svc_tok
        resolved["identity_type"] = "KeyID"
        # Server mints a KeyID identity per physical tunnel + sets remote_id=infoblox.cloud.
        for tc in resolved.get("tunnel_configs", []):
            tc.setdefault("id", _tok())
            tc["remote_id"] = "infoblox.cloud"
            for pt in tc.get("physical_tunnels", []):
                pt["identity"] = uuid4().hex[:16]
                pt["remote_id"] = "infoblox.cloud"
                pt["status"] = "Not Ready"
        _access_locations[atok] = resolved
        created_als.append(resolved)

    # Response shape for consolidated/configure: note cnames are NOT here — the endpoint
    # provisions async; clients GET /endpoints for cnames.
    return {
        "universal_service": svc.model_dump(),
        "endpoints": {"created": [
            {k: v for k, v in e.model_dump().items() if k != "cnames"} for e in created_endpoints]},
        "access_locations": {"created": created_als},
    }


# ---- Read-back ----

@app.get("/api/universalinfra/v1/universalservices")
def list_services(authorization: str | None = Header(default=None)):
    _require_token(authorization)
    return {"results": [s.model_dump() for s in _services.values()]}


@app.get("/api/universalinfra/v1/universalservices/{token}")
def get_service(token: str, authorization: str | None = Header(default=None)):
    _require_token(authorization)
    if token not in _services:
        raise HTTPException(status_code=404, detail="service not found")
    return {"result": _services[token].model_dump()}


@app.get("/api/universalinfra/v1/endpoints")
@app.get("/api/universalinfra/v1/endpoints/")
def list_endpoints(authorization: str | None = Header(default=None)):
    _require_token(authorization)
    return {"results": [e.model_dump() for e in _endpoints.values()]}


@app.get("/api/universalinfra/v1/endpoints/{token}")
def get_endpoint(token: str, authorization: str | None = Header(default=None)):
    _require_token(authorization)
    if token not in _endpoints:
        raise HTTPException(status_code=404, detail="endpoint not found")
    return {"result": _endpoints[token].model_dump()}


@app.get("/api/universalinfra/v1/accesslocations")
def list_access_locations(authorization: str | None = Header(default=None)):
    _require_token(authorization)
    return {"results": list(_access_locations.values())}


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
