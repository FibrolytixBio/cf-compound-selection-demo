#!/usr/bin/env python3
"""
ChEMBL Standalone Functions - Standalone functions for ChEMBL chemical database queries

This module provides clean standalone functions extracted from the ChEMBL MCP server.
Functions use typed annotations for better IDE support and runtime validation.
"""

from typing import Optional, Dict, Any, Annotated

import httpx
from pydantic import Field


CHEMBL_BASE_URL = "https://www.ebi.ac.uk/chembl/api/data"
TIMEOUT = 30.0


class ChEMBLClient:
    """HTTP client for ChEMBL API interactions"""

    def __init__(self):
        self.client = httpx.AsyncClient(
            base_url=CHEMBL_BASE_URL,
            timeout=TIMEOUT,
            headers={
                "User-Agent": "ChEMBL-Functions/1.0.0",
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


# ==================== Compound Search & Information ====================


async def search_compounds(
    query: Annotated[
        str,
        Field(description="Search query (compound name, synonym, or identifier)"),
    ],
    limit: Annotated[
        int,
        Field(
            default=10,
            ge=1,
            le=1000,
            description="Number of results to return (1-1000)",
        ),
    ] = 10,
) -> Dict[str, Any]:
    """Search ChEMBL database for compounds by name, synonym, or identifier"""
    params = {
        "q": query,
        "limit": limit,
    }
    return await chembl_client.get("/molecule/search.json", params=params)


async def get_compound_bioactivities(
    chembl_id: Annotated[
        str, Field(description="ChEMBL ID of the compound (e.g., CHEMBL25)")
    ],
    max_results: Annotated[
        Optional[int],
        Field(
            default=10,
            description="Maximum number of results to return (1–1000), lower values recommended",
        ),
    ] = 10,
    activity_type: Annotated[
        Optional[str],
        Field(
            default=None,
            description="Standard activity type to filter by (e.g., IC50, Ki)",
        ),
    ] = None,
    max_activity_value: Annotated[
        Optional[float],
        Field(
            default=None,
            description="Maximum allowed activity value (e.g., IC50 < X nM)",
        ),
    ] = None,
) -> Dict[str, Any]:
    """Retrieve all reported bioactivities for a given ChEMBL compound."""
    params = {
        "molecule_chembl_id": chembl_id,
        "limit": max_results,
    }
    if activity_type is not None:
        params["standard_type"] = activity_type
    if max_activity_value is not None:
        params["standard_value__lt"] = max_activity_value

    return await chembl_client.get("/activity.json", params=params)


async def get_activity_info(
    activity_id: Annotated[
        int, Field(description="Numeric ChEMBL activity ID (e.g., 363803)")
    ],
) -> Dict[str, Any]:
    """Return the full ChEMBL activity record for a specific activity."""
    return await chembl_client.get(
        "/activity.json",
        params={"activity_id": activity_id},
    )


async def get_assay_info(
    assay_id: Annotated[str, Field(description="ChEMBL assay ID (e.g., CHEMBL761638)")],
) -> Dict[str, Any]:
    """Return ChEMBL assay metadata for a specific assay."""
    return await chembl_client.get(
        "/assay.json",
        params={"assay_chembl_id": assay_id},
    )


async def get_mechanisms_of_action(
    chembl_id: Annotated[
        str, Field(description="ChEMBL ID of the compound (e.g., CHEMBL25)")
    ],
    max_results: Annotated[
        int,
        Field(
            default=10,
            ge=1,
            le=1000,
            description="Maximum number of results to return (1–1000)",
        ),
    ] = 10,
) -> Dict[str, Any]:
    """Return ChEMBL's curated mechanism of action data for a given compound."""
    return await chembl_client.get(
        "/mechanism.json",
        params={
            "molecule_chembl_id": chembl_id,
            "limit": max_results,
        },
    )


async def get_molecule_info(
    chembl_id: Annotated[
        str, Field(description="ChEMBL ID of the compound (e.g., CHEMBL25)")
    ],
    max_results: Annotated[
        int,
        Field(
            default=10,
            ge=1,
            le=1000,
            description="Maximum number of results to return (1–1000)",
        ),
    ] = 10,
) -> Dict[str, Any]:
    """Return ChEMBL's curated properties and metadata for a given compound, including calculated drug properties."""
    return await chembl_client.get(
        "/molecule.json",
        params={
            "molecule_chembl_id": chembl_id,
            "limit": max_results,
        },
    )


async def get_drug_info(
    chembl_id: Annotated[
        str, Field(description="ChEMBL ID of the compound (e.g., CHEMBL25)")
    ],
    max_results: Annotated[
        int,
        Field(
            default=10,
            ge=1,
            le=1000,
            description="Maximum number of results to return (1–1000)",
        ),
    ] = 10,
) -> Dict[str, Any]:
    """Return drug info for a given compound, including drug name, type, and status."""
    return await chembl_client.get(
        "/drug.json",
        params={
            "molecule_chembl_id": chembl_id,
            "limit": max_results,
        },
    )


async def get_drug_indications(
    chembl_id: Annotated[
        str, Field(description="ChEMBL ID of the compound (e.g., CHEMBL25)")
    ],
    max_results: Annotated[
        int,
        Field(
            default=10,
            ge=1,
            le=1000,
            description="Maximum number of results to return (1–1000)",
        ),
    ] = 10,
) -> Dict[str, Any]:
    """Return drug indications for a given compound, including disease and max phase."""
    return await chembl_client.get(
        "/drug_indication.json",
        params={
            "molecule_chembl_id": chembl_id,
            "limit": max_results,
        },
    )


async def get_drug_warning(
    chembl_id: Annotated[
        str, Field(description="ChEMBL ID of the compound (e.g., CHEMBL25)")
    ],
    max_results: Annotated[
        int,
        Field(
            default=10,
            ge=1,
            le=1000,
            description="Maximum number of results to return (1–1000)",
        ),
    ] = 10,
) -> Dict[str, Any]:
    """Return drug warnings for a given compound."""
    return await chembl_client.get(
        "/drug_warning.json",
        params={
            "molecule_chembl_id": chembl_id,
            "limit": max_results,
        },
    )


# ==================== Target Search & Information ====================


async def search_targets(
    query: Annotated[
        str,
        Field(description="Search query (target name, gene symbol, or ChEMBL ID)"),
    ],
    limit: Annotated[
        int,
        Field(
            default=10,
            ge=1,
            le=1000,
            description="Number of results to return (1–1000)",
        ),
    ] = 10,
) -> Dict[str, Any]:
    """Search ChEMBL database for biological targets by name, gene symbol, or identifier"""
    params = {
        "q": query,
        "limit": limit,
    }
    return await chembl_client.get("/target/search.json", params=params)


async def get_target_information(
    target_chembl_id: Annotated[
        str, Field(description="ChEMBL Target ID (e.g., CHEMBL204)")
    ],
    max_results: Annotated[
        int,
        Field(
            default=10,
            ge=1,
            le=1000,
            description="Maximum number of results to return (1–1000)",
        ),
    ] = 10,
) -> Dict[str, Any]:
    """Return biological details for a ChEMBL target (e.g., UniProt ID, GO terms)."""
    return await chembl_client.get(
        "/target.json",
        params={
            "target_chembl_id": target_chembl_id,
            "limit": max_results,
        },
    )


async def get_active_compounds(
    target_chembl_id: Annotated[
        str, Field(description="ChEMBL ID of the target (e.g., CHEMBL204)")
    ],
    max_results: Annotated[
        Optional[int],
        Field(default=10, description="Maximum number of results to return (1–1000)"),
    ] = 10,
    activity_type: Annotated[
        Optional[str],
        Field(default=None, description="Activity type to filter by (e.g., IC50, Ki)"),
    ] = None,
    max_activity_value: Annotated[
        Optional[float],
        Field(default=None, description="Maximum allowed activity value in nM"),
    ] = None,
) -> Dict[str, Any]:
    """Retrieve active compounds against a specific ChEMBL target with a potency filter."""
    params = {
        "target_chembl_id": target_chembl_id,
        "limit": max_results,
    }
    if activity_type is not None:
        params["standard_type"] = activity_type
    if max_activity_value is not None:
        params["standard_value__lt"] = max_activity_value

    return await chembl_client.get("/activity.json", params=params)


# ============================ Function List ============================

CHEMBL_TOOLS = [
    search_compounds,
    get_compound_bioactivities,
    get_activity_info,
    get_assay_info,
    get_mechanisms_of_action,
    get_molecule_info,
    get_drug_info,
    get_drug_indications,
    get_drug_warning,
    search_targets,
    get_target_information,
    get_active_compounds,
]
