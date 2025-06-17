#!/usr/bin/env python3
"""
ChEMBL MCP Server - A Model Context Protocol server for ChEMBL chemical database
"""

from typing import Optional, Dict, Any

import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from agentic_system.tools.tool_utils import mcp_tool_with_prefix


# Create an MCP server
mcp = FastMCP("ChEMBL MCP Server")
# add server prefix to tool names
mcp.tool = mcp_tool_with_prefix(mcp, "CHEMBL")

# ChEMBL API client configuration
CHEMBL_BASE_URL = "https://www.ebi.ac.uk/chembl/api/data"
TIMEOUT = 30.0


class ChEMBLClient:
    """HTTP client for ChEMBL API interactions"""

    def __init__(self):
        self.client = httpx.AsyncClient(
            base_url=CHEMBL_BASE_URL,
            timeout=TIMEOUT,
            headers={
                "User-Agent": "ChEMBL-MCP-Server/1.0.0",
                "Accept": "application/json",
            },
        )

    async def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make GET request to ChEMBL API"""
        response = await self.client.get(endpoint, params=params)
        response.raise_for_status()
        return response.json()


# Initialize the ChEMBL client
chembl_client = ChEMBLClient()

# ============================ Compound Tools =============================


class CompoundSearchRequest(BaseModel):
    query: str = Field(
        description="Search query (compound name, synonym, or identifier)"
    )
    limit: int = Field(
        default=10, ge=1, le=1000, description="Number of results to return (1-1000)"
    )


@mcp.tool()
async def search_compounds(request: CompoundSearchRequest) -> Dict[str, Any]:
    """Search ChEMBL database for compounds by name, synonym, or identifier"""
    params = {
        "q": request.query,
        "limit": request.limit,
    }
    return await chembl_client.get("/molecule/search.json", params=params)


class CompoundBioactivitiesRequest(BaseModel):
    chembl_id: str = Field(description="ChEMBL ID of the compound (e.g., CHEMBL25)")
    max_results: Optional[int] = Field(
        default=10,
        description="Maximum number of results to return (1–1000), lower values recommended",
    )
    activity_type: Optional[str] = Field(
        default=None, description="Standard activity type to filter by (e.g., IC50, Ki)"
    )
    max_activity_value: Optional[float] = Field(
        default=None, description="Maximum allowed activity value (e.g., IC50 < X nM)"
    )


@mcp.tool()
async def get_compound_bioactivities(
    request: CompoundBioactivitiesRequest,
) -> Dict[str, Any]:
    """Retrieve all reported bioactivities for a given ChEMBL compound."""
    params = {
        "molecule_chembl_id": request.chembl_id,
        "limit": request.max_results,
    }
    if request.activity_type is not None:
        params["standard_type"] = request.activity_type
    if request.max_activity_value is not None:
        params["standard_value__lt"] = request.max_activity_value

    return await chembl_client.get("/activity.json", params=params)


class ActivityInfoRequest(BaseModel):
    activity_id: int = Field(description="Numeric ChEMBL activity ID (e.g., 363803)")


@mcp.tool()
async def get_activity_info(request: ActivityInfoRequest) -> Dict[str, Any]:
    """Return the full ChEMBL activity record for a specific activity."""
    return await chembl_client.get(
        "/activity.json",
        params={"activity_id": request.activity_id},
    )


class AssayInfoRequest(BaseModel):
    assay_id: str = Field(description="ChEMBL assay ID (e.g., CHEMBL761638)")


@mcp.tool()
async def get_assay_info(request: AssayInfoRequest) -> Dict[str, Any]:
    """Return ChEMBL assay metadata for a specific assay."""
    return await chembl_client.get(
        "/assay.json",
        params={"assay_chembl_id": request.assay_id},
    )


class CompoundRequest(BaseModel):
    chembl_id: str = Field(description="ChEMBL ID of the compound (e.g., CHEMBL25)")
    max_results: int = Field(
        default=10,
        ge=1,
        le=1000,
        description="Maximum number of results to return (1–1000)",
    )


@mcp.tool()
async def get_mechanisms_of_action(request: CompoundRequest) -> Dict[str, Any]:
    """Return ChEMBL’s curated mechanism of action data for a given compound."""
    return await chembl_client.get(
        "/mechanism.json",
        params={
            "molecule_chembl_id": request.chembl_id,
            "limit": request.max_results,
        },
    )


@mcp.tool()
async def get_molecule_info(request: CompoundRequest) -> Dict[str, Any]:
    """Return ChEMBL’s curated properties and metadata for a given compound, including calculated drug properties."""
    return await chembl_client.get(
        "/molecule.json",
        params={
            "molecule_chembl_id": request.chembl_id,
            "limit": request.max_results,
        },
    )


@mcp.tool()
async def get_drug_info(request: CompoundRequest) -> Dict[str, Any]:
    """Return drug info for a given compound, including drug name, type, and status."""
    return await chembl_client.get(
        "/drug.json",
        params={
            "molecule_chembl_id": request.chembl_id,
            "limit": request.max_results,
        },
    )


@mcp.tool()
async def get_drug_indications(request: CompoundRequest) -> Dict[str, Any]:
    """Return drug indications for a given compound, including disease and max phase."""
    return await chembl_client.get(
        "/drug_indication.json",
        params={
            "molecule_chembl_id": request.chembl_id,
            "limit": request.max_results,
        },
    )


@mcp.tool()
async def get_drug_warning(request: CompoundRequest) -> Dict[str, Any]:
    """Return drug warnings for a given compound."""
    return await chembl_client.get(
        "/drug_warning.json",
        params={
            "molecule_chembl_id": request.chembl_id,
            "limit": request.max_results,
        },
    )


# ============================ Target Tools ============================


class TargetSearchRequest(BaseModel):
    query: str = Field(
        description="Search query (target name, gene symbol, or ChEMBL ID)"
    )
    limit: int = Field(
        default=10, ge=1, le=1000, description="Number of results to return (1–1000)"
    )


@mcp.tool()
async def search_targets(request: TargetSearchRequest) -> Dict[str, Any]:
    """Search ChEMBL database for biological targets by name, gene symbol, or identifier"""
    params = {
        "q": request.query,
        "limit": request.limit,
    }
    return await chembl_client.get("/target/search.json", params=params)


class TargetInformationRequest(BaseModel):
    target_chembl_id: str = Field(description="ChEMBL Target ID (e.g., CHEMBL204)")
    max_results: int = Field(
        default=10,
        ge=1,
        le=1000,
        description="Maximum number of results to return (1–1000)",
    )


@mcp.tool()
async def get_target_information(request: TargetInformationRequest) -> Dict[str, Any]:
    """Return biological details for a ChEMBL target (e.g., UniProt ID, GO terms)."""
    return await chembl_client.get(
        "/target.json",
        params={
            "target_chembl_id": request.target_chembl_id,
            "limit": request.max_results,
        },
    )


class ActiveCompoundsRequest(BaseModel):
    target_chembl_id: str = Field(
        description="ChEMBL ID of the target (e.g., CHEMBL204)"
    )
    max_results: Optional[int] = Field(
        default=10, description="Maximum number of results to return (1–1000)"
    )
    activity_type: Optional[str] = Field(
        default=None, description="Activity type to filter by (e.g., IC50, Ki)"
    )
    max_activity_value: Optional[float] = Field(
        default=None, description="Maximum allowed activity value in nM"
    )


@mcp.tool()
async def get_active_compounds(request: ActiveCompoundsRequest) -> Dict[str, Any]:
    """Retrieve active compounds against a specific ChEMBL target with a potency filter."""
    params = {
        "target_chembl_id": request.target_chembl_id,
        "limit": request.max_results,
    }
    if request.activity_type is not None:
        params["standard_type"] = request.activity_type
    if request.max_activity_value is not None:
        params["standard_value__lt"] = request.max_activity_value

    return await chembl_client.get("/activity.json", params=params)


if __name__ == "__main__":
    mcp.run()
