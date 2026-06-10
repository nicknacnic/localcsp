"""The create path: consolidated/configure → read back cnames from /endpoints.

Payload + constraints follow the documented shape (docs/api-model.md): inline location with
country, one connection with >=2 physical tunnels, server-minted KeyID identities +
remote_id=infoblox.cloud, cnames absent from the create response. All addresses below are
example/documentation ranges.
"""
from fastapi.testclient import TestClient

from localcsp.app import app

AUTH = {"Authorization": "Token test-key"}
client = TestClient(app)
CONFIGURE = "/api/universalinfra/v1/consolidated/configure"
EP = "/api/universalinfra/v1/endpoints"
AL = "/api/universalinfra/v1/accesslocations"

PAYLOAD = {
    "universal_service": {"operation": "CREATE", "name": "example-xaas",
                          "capabilities": [{"type": "dns"}]},
    "locations": {"create": [
        {"id": "ref_loc", "name": "example-edge-ashburn",
         "address": {"city": "Ashburn", "state": "Virginia",
                     "country": "United States of America", "postal_code": "20147"}}
    ]},
    "endpoints": {"create": [
        {"id": "ref_ep", "name": "example-xaas-sd", "size": "S",
         "service_location": "AWS US East (N. Virginia)",
         "service_ip": "192.0.2.10", "neighbour_ips": ["192.0.2.11", "192.0.2.12"],
         "preferred_provider": "AWS", "routing_type": "static"}
    ]},
    "access_locations": {"create": [
        {"endpoint_id": "ref_ep", "id": "ref_al", "location_id": "ref_loc",
         "routing_type": "static", "type": "Site", "name": "example-al",
         "lan_subnets": ["192.0.2.0/24"],
         "tunnel_configs": [
            {"name": "example-conn", "wan_ip": "203.0.113.1", "physical_tunnels": [
                {"path": "primary", "credential_id": "ref_cred", "index": 0, "access_ip": "203.0.113.1"},
                {"path": "secondary", "credential_id": "ref_cred", "index": 1, "access_ip": "203.0.113.1"}]},
         ]}
    ]},
}


def test_requires_token():
    assert client.post(CONFIGURE, json=PAYLOAD).status_code == 401


def test_configure_creates_and_mints_identities():
    r = client.post(CONFIGURE, headers=AUTH, json=PAYLOAD).json()
    assert r["universal_service"]["id"].startswith("infra/universal_service/")
    # cnames are NOT in the create response (endpoint provisions async).
    assert "cnames" not in r["endpoints"]["created"][0]

    al = r["access_locations"]["created"][0]
    pts = al["tunnel_configs"][0]["physical_tunnels"]
    assert len(pts) == 2
    assert all(pt["remote_id"] == "infoblox.cloud" for pt in pts)
    assert pts[0]["identity"] != pts[1]["identity"]  # distinct minted KeyIDs
    assert al["identity_type"] == "KeyID"

    # Read-back via the verified GETs.
    assert client.get(EP, headers=AUTH).json()["results"]
    assert client.get(AL, headers=AUTH).json()["results"]


def test_location_must_have_country():
    bad = {**PAYLOAD, "locations": {"create": [{"id": "ref_loc", "name": "x", "address": {}}]}}
    assert client.post(CONFIGURE, headers=AUTH, json=bad).status_code == 500


def test_min_two_physical_tunnels():
    bad = {**PAYLOAD, "access_locations": {"create": [
        {"endpoint_id": "ref_ep", "id": "ref_al", "location_id": "ref_loc", "type": "Site",
         "name": "x", "tunnel_configs": [
            {"name": "c", "wan_ip": "203.0.113.1", "physical_tunnels": [
                {"path": "primary", "credential_id": "c", "index": 0}]}]}]}}
    assert client.post(CONFIGURE, headers=AUTH, json=bad).status_code == 400


def test_access_location_requires_location_id():
    bad = {**PAYLOAD, "access_locations": {"create": [
        {"endpoint_id": "ref_ep", "id": "ref_al", "type": "Site", "name": "x",
         "tunnel_configs": [{"name": "c", "physical_tunnels": [
            {"path": "primary"}, {"path": "secondary"}]}]}]}}
    assert client.post(CONFIGURE, headers=AUTH, json=bad).status_code == 400
