"""Read-back object model for NIOS-X as a Service, following the documented GET shapes.

The create request shape is intentionally NOT modeled as strict types — it's the nested,
ref-linked `consolidated/configure` payload, accepted as a dict in app.py.
"""
from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field

CapabilityType = Literal["dns", "dhcp", "security", "dfp", "ntp"]


class Capability(BaseModel):
    type: CapabilityType
    service_status: str = "Available"
    profile_id: Optional[str] = None
    profile_name: Optional[str] = None


class UniversalService(BaseModel):
    id: str            # "infra/universal_service/<token>"
    name: str
    ophid: str
    capabilities: list[Capability] = Field(default_factory=lambda: [Capability(type="dns")])


class Endpoint(BaseModel):
    """Service Deployment (POP). cnames = the two Cloud Service IPs (minted, public IKE peers)."""
    id: str            # "infra/endpoint/<token>"
    name: str
    universal_service_id: str
    service_location: str          # e.g. "AWS US East (N. Virginia)"
    service_ip: str                # private /32 the DNS capability listens on
    neighbour_ips: list[str]       # [primary_source_ip, secondary_source_ip]
    cnames: list[str] = Field(default_factory=list)
    size: Literal["S", "M", "L", "XL"] = "S"
    routing_type: Literal["static", "dynamic"] = "static"
    preferred_provider: str = "Any"
    routing_config: dict = Field(default_factory=dict)
    object: str = "endpoint"
