#!/usr/bin/env python3
"""
ChEMBL Standalone Tools - Synchronous functions with natural language outputs
"""

from typing import Dict, Any
import httpx
from agentic_system.tools.tool_utils import (
    FileBasedRateLimiter,
    tool_cache,
    ai_summarized_output,
)


# ChEMBL API client configuration
CHEMBL_BASE_URL = "https://www.ebi.ac.uk/chembl/api/data"
TIMEOUT = 30.0


class ChEMBLClient:
    """HTTP client for ChEMBL API interactions"""

    def __init__(self):
        self.client = httpx.Client(
            base_url=CHEMBL_BASE_URL,
            timeout=TIMEOUT,
            headers={
                "User-Agent": "ChEMBL-Tools/1.0.0",
                "Accept": "application/json",
            },
        )
        self.rate_limiter = FileBasedRateLimiter(
            max_requests=2, time_window=1.0, name="chembl"
        )

    def get(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make GET request to ChEMBL API"""
        self.rate_limiter.acquire_sync()
        try:
            response = self.client.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return {
                "error": f"API error: {e.response.status_code} - {e.response.text[:100]}"
            }
        except Exception as e:
            return {"error": f"Request failed: {str(e)}"}


# Initialize the ChEMBL client
chembl_client = ChEMBLClient()
cache_name = "chembl"

# ============================ Compound Search Tools =============================


@tool_cache(cache_name)
def search_chembl_id(query: str, limit: int = 5) -> str:
    """Search for ChEMBL IDs by compound name, synonym, or identifier. Returns only the ChEMBL IDs for efficient lookup.

    Args:
        query (str): Compound name, synonym, or identifier to search for
        limit (int, optional): Maximum number of results to return (1-10). Defaults to 5.

    Returns:
        str: Natural language summary of search results
    """
    params = {
        "q": query,
        "limit": limit,
    }
    result = chembl_client.get("/molecule/search.json", params=params)

    if "error" in result:
        return f"Error searching for compound: {result['error']}"

    molecules = result.get("molecules", [])
    if not molecules:
        return f"No compounds found matching '{query}'"

    # Extract just the ChEMBL IDs and preferred names
    compounds = []
    for mol in molecules[:limit]:
        chembl_id = mol.get("molecule_chembl_id", "Unknown")
        pref_name = mol.get("pref_name", "No name")
        compounds.append(f"{chembl_id} ({pref_name})")

    return (
        f"Found {len(compounds)} compound(s) matching '{query}': \n - "
        + "\n - ".join(compounds)
    )


@tool_cache(cache_name)
def get_compound_bioactivities(
    chembl_id: str,
    max_results: int = 10,
    activity_type: str = None,
    max_activity_value: float = None,
) -> str:
    """Retrieve all reported bioactivities for a given ChEMBL compound.

    Args:
        chembl_id (str): ChEMBL ID of the compound (e.g., CHEMBL25)
        max_results (int, optional): Maximum number of results to return (1–1000). Defaults to 10.
        activity_type (str, optional): Standard activity type to filter by (e.g., IC50, Ki). Defaults to None.
        max_activity_value (float, optional): Maximum allowed activity value (e.g., IC50 < X nM). Defaults to None.
        goal (str, optional): The goal for summarization, defaults to decorator's goal.

    Returns:
        str: AI-summarized summary of bioactivity data, formatted for use by larger models
    """
    params = {
        "molecule_chembl_id": chembl_id,
        "limit": max_results,
    }
    if activity_type is not None:
        params["standard_type"] = activity_type
    if max_activity_value is not None:
        params["standard_value__lt"] = max_activity_value

    return chembl_client.get("/activity.json", params=params)


@tool_cache(cache_name)
def get_activity_info(activity_id: int) -> Dict[str, Any]:
    """Return the full ChEMBL activity record for a specific activity.

    Args:
        activity_id (int): Numeric ChEMBL activity ID (e.g., 363803)

    Returns:
        Dict[str, Any]: Raw ChEMBL API response with activity record
    """
    return chembl_client.get(
        "/activity.json",
        params={"activity_id": activity_id},
    )


@tool_cache(cache_name)
def get_assay_info(assay_id: str) -> Dict[str, Any]:
    """Return ChEMBL assay metadata for a specific assay.

    Args:
        assay_id (str): ChEMBL assay ID (e.g., CHEMBL761638)

    Returns:
        Dict[str, Any]: Raw ChEMBL API response with assay metadata
    """
    return chembl_client.get(
        "/assay.json",
        params={"assay_chembl_id": assay_id},
    )


@tool_cache(cache_name)
def get_mechanisms_of_action(chembl_id: str, max_results: int = 10) -> Dict[str, Any]:
    """Return ChEMBL's curated mechanism of action data for a given compound.

    Args:
        chembl_id (str): ChEMBL ID of the compound (e.g., CHEMBL25)
        max_results (int, optional): Maximum number of results to return (1–1000). Defaults to 10.

    Returns:
        Dict[str, Any]: Raw ChEMBL API response with mechanism of action data
    """
    return chembl_client.get(
        "/mechanism.json",
        params={
            "molecule_chembl_id": chembl_id,
            "limit": max_results,
        },
    )


@tool_cache(cache_name)
def get_molecule_info(chembl_id: str, max_results: int = 10) -> Dict[str, Any]:
    """Return ChEMBL's curated properties and metadata for a given compound, including calculated drug properties.

    Args:
        chembl_id (str): ChEMBL ID of the compound (e.g., CHEMBL25)
        max_results (int, optional): Maximum number of results to return (1–1000). Defaults to 10.

    Returns:
        Dict[str, Any]: Raw ChEMBL API response with molecule information and properties
    """
    return chembl_client.get(
        "/molecule.json",
        params={
            "molecule_chembl_id": chembl_id,
            "limit": max_results,
        },
    )


@tool_cache(cache_name)
def get_drug_info(chembl_id: str, max_results: int = 10) -> Dict[str, Any]:
    """Return drug info for a given compound, including drug name, type, and status.

    Args:
        chembl_id (str): ChEMBL ID of the compound (e.g., CHEMBL25)
        max_results (int, optional): Maximum number of results to return (1–1000). Defaults to 10.

    Returns:
        Dict[str, Any]: Raw ChEMBL API response with drug information
    """
    return chembl_client.get(
        "/drug.json",
        params={
            "molecule_chembl_id": chembl_id,
            "limit": max_results,
        },
    )


@tool_cache(cache_name)
def get_drug_indications(chembl_id: str, max_results: int = 10) -> Dict[str, Any]:
    """Return drug indications for a given compound, including disease and max phase.

    Args:
        chembl_id (str): ChEMBL ID of the compound (e.g., CHEMBL25)
        max_results (int, optional): Maximum number of results to return (1–1000). Defaults to 10.

    Returns:
        Dict[str, Any]: Raw ChEMBL API response with drug indications
    """
    return chembl_client.get(
        "/drug_indication.json",
        params={
            "molecule_chembl_id": chembl_id,
            "limit": max_results,
        },
    )


@tool_cache(cache_name)
def get_drug_warning(chembl_id: str, max_results: int = 10) -> Dict[str, Any]:
    """Return drug warnings for a given compound.

    Args:
        chembl_id (str): ChEMBL ID of the compound (e.g., CHEMBL25)
        max_results (int, optional): Maximum number of results to return (1–1000). Defaults to 10.

    Returns:
        Dict[str, Any]: Raw ChEMBL API response with drug warnings
    """
    return chembl_client.get(
        "/drug_warning.json",
        params={
            "molecule_chembl_id": chembl_id,
            "limit": max_results,
        },
    )


# ============================ Target Tools =============================


@tool_cache(cache_name)
def search_targets(query: str, limit: int = 10) -> Dict[str, Any]:
    """Search ChEMBL database for biological targets by name, gene symbol, or identifier.

    Args:
        query (str): Search query (target name, gene symbol, or ChEMBL ID)
        limit (int, optional): Number of results to return (1–1000). Defaults to 10.

    Returns:
        Dict[str, Any]: Raw ChEMBL API response with target search results
    """
    params = {
        "q": query,
        "limit": limit,
    }
    return chembl_client.get("/target/search.json", params=params)


@tool_cache(cache_name)
def get_target_information(
    target_chembl_id: str, max_results: int = 10
) -> Dict[str, Any]:
    """Return biological details for a ChEMBL target (e.g., UniProt ID, GO terms).

    Args:
        target_chembl_id (str): ChEMBL Target ID (e.g., CHEMBL204)
        max_results (int, optional): Maximum number of results to return (1–1000). Defaults to 10.

    Returns:
        Dict[str, Any]: Raw ChEMBL API response with target information
    """
    return chembl_client.get(
        "/target.json",
        params={
            "target_chembl_id": target_chembl_id,
            "limit": max_results,
        },
    )


@tool_cache(cache_name)
def get_active_compounds(
    target_chembl_id: str,
    max_results: int = 10,
    activity_type: str = None,
    max_activity_value: float = None,
) -> Dict[str, Any]:
    """Retrieve active compounds against a specific ChEMBL target with a potency filter.

    Args:
        target_chembl_id (str): ChEMBL ID of the target (e.g., CHEMBL204)
        max_results (int, optional): Maximum number of results to return (1–1000). Defaults to 10.
        activity_type (str, optional): Activity type to filter by (e.g., IC50, Ki). Defaults to None.
        max_activity_value (float, optional): Maximum allowed activity value in nM. Defaults to None.

    Returns:
        Dict[str, Any]: Raw ChEMBL API response with active compounds data
    """
    params = {
        "target_chembl_id": target_chembl_id,
        "limit": max_results,
    }
    if activity_type is not None:
        params["standard_type"] = activity_type
    if max_activity_value is not None:
        params["standard_value__lt"] = max_activity_value

    return chembl_client.get("/activity.json", params=params)


# ============================ Function List ============================

CHEMBL_TOOLS = [
    search_chembl_id,
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

for i, fn in enumerate(CHEMBL_TOOLS):
    wrapped = ai_summarized_output(fn)
    wrapped.__name__ = "CHEMBL__" + wrapped.__name__
    CHEMBL_TOOLS[i] = wrapped


if __name__ == "__main__":
    import dotenv

    dotenv.load_dotenv("../../../.env")

    # test get_active_compounds
    result = get_active_compounds("CHEMBL4303", activity_type="IC50", max_results=5)

    # print(get_compound_bioactivities("CHEMBL252164", max_results=5))
    print(CHEMBL_TOOLS[1]("CHEMBL252164", max_results=5))
