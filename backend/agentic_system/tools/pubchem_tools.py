#!/usr/bin/env python3
"""
PubChem Standalone Tools - Synchronous functions with natural language outputs
"""

from typing import Dict, Any, Union, List
import urllib.parse
import time

import httpx
from agentic_system.tools.tool_utils import (
    FileBasedRateLimiter,
    tool_cache,
    ai_summarized_output,
)


# PubChem API client configuration
PUBCHEM_BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
TIMEOUT = 30.0


class PubChemClient:
    """HTTP client for PubChem API interactions (synchronous)"""

    def __init__(self):
        self.client = httpx.Client(
            base_url=PUBCHEM_BASE_URL,
            timeout=TIMEOUT,
            headers={
                "User-Agent": "PubChem-Tools/1.0.0",
                "Accept": "application/json",
            },
        )
        self.rate_limiter = FileBasedRateLimiter(
            max_requests=2, time_window=1.0, name="pubchem"
        )

    def get(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make GET request to PubChem API"""
        self.rate_limiter.acquire_sync()
        try:
            response = self.client.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return {
                "error": f"API error: {e.response.status_code} - {e.response.text[:200]}"
            }
        except Exception as e:
            return {"error": f"Request failed: {str(e)}"}

    def post(
        self,
        endpoint: str,
        params: Dict[str, Any] = None,
        data: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Make POST request to PubChem API"""
        self.rate_limiter.acquire_sync()
        try:
            response = self.client.post(endpoint, params=params, data=data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return {
                "error": f"API error: {e.response.status_code} - {e.response.text[:200]}"
            }
        except Exception as e:
            return {"error": f"Request failed: {str(e)}"}


# Initialize the PubChem client
pubchem_client = PubChemClient()
cache_name = "pubchem"


# ==================== Chemical Search & Retrieval ====================


@tool_cache(cache_name)
def search_pubchem_cid(query: str, limit: int = 5) -> str:
    """Search for PubChem CIDs by compound name, CAS number, or formula. Returns CIDs and key names.

    Args:
        query (str): Compound name, CAS number, or molecular formula to search for
        limit (int, optional): Number of results to return (1-10). Defaults to 5.

    Returns:
        str: Natural language summary of search results
    """
    endpoint = f"/compound/name/{urllib.parse.quote(query)}/cids/JSON"
    result = pubchem_client.get(endpoint, params={"MaxRecords": limit})

    if "error" in result:
        return f"Error searching for compound: {result['error']}"

    cids: List[int] = result.get("IdentifierList", {}).get("CID", [])
    if not cids:
        return f"No compounds found matching '{query}'"

    # If single CID, enrich with IUPAC name; if many, just list CIDs
    if len(cids) == 1:
        props_endpoint = f"/compound/cid/{cids[0]}/property/IUPACName/JSON"
        props_result = pubchem_client.get(props_endpoint)
        if "error" not in props_result and props_result.get("PropertyTable"):
            name = props_result["PropertyTable"]["Properties"][0].get("IUPACName", "")
            return f"Found PubChem CID {cids[0]} ({name}) for '{query}'"

    return (
        f"Found {min(len(cids), limit)} compound(s) matching '{query}': CIDs \n - "
        + "\n - ".join(map(str, cids[:limit]))
    )


@tool_cache(cache_name)
def get_compound_info(cid: Union[int, str], format: str = "json") -> Dict[str, Any]:
    """Retrieve detailed information for a specific compound by PubChem CID.

    Args:
        cid (Union[int, str]): PubChem Compound ID (CID) to retrieve information for
        format (str, optional): Output format to return (e.g., json, xml, etc.). Defaults to "json".

    Returns:
        Dict[str, Any]: Raw PubChem API response with detailed compound information
    """
    response = pubchem_client.get(f"/compound/cid/{cid}/{format.upper()}")
    return response


@tool_cache(cache_name)
def get_compound_synonyms(cid: Union[int, str]) -> Dict[str, Any]:
    """Get all names and synonyms for a compound.

    Args:
        cid (Union[int, str]): PubChem Compound ID (CID)

    Returns:
        Dict[str, Any]: Raw PubChem API response with compound synonyms and names
    """
    endpoint = f"/compound/cid/{cid}/synonyms/JSON"
    response = pubchem_client.get(endpoint)
    return response


# # ==================== Structure Analysis & Similarity ====================


@tool_cache(cache_name)
def search_similar_compounds(
    smiles: str, threshold: int = 90, max_records: int = 10
) -> Dict[str, Any]:
    """Find chemically similar compounds using Tanimoto similarity.

    Args:
        smiles (str): SMILES string of the query molecule
        threshold (int, optional): Similarity threshold (0–100). Defaults to 90.
        max_records (int, optional): Maximum number of results (1–100). Defaults to 10.

    Returns:
        Dict[str, Any]: Similarity search results with similar compound information
    """
    endpoint = "/compound/similarity/smiles/JSON"
    params = {"Threshold": threshold, "MaxRecords": max_records}
    data = {"smiles": smiles}

    result = pubchem_client.post(endpoint, params=params, data=data)
    list_key = result["Waiting"]["ListKey"]
    return _poll_for_results(list_key)


@tool_cache(cache_name)
def substructure_search(smiles: str, max_records: int = 10) -> Dict[str, Any]:
    """Find compounds containing a specific substructure.

    Args:
        smiles (str): SMILES string of the substructure query
        max_records (int, optional): Maximum number of results (1–10000). Defaults to 10.

    Returns:
        Dict[str, Any]: Substructure search results with matching compounds
    """
    endpoint = "/compound/substructure/smiles/JSON"
    data = {"smiles": smiles}
    params = {"MaxRecords": max_records}

    result = pubchem_client.post(endpoint, params=params, data=data)
    list_key = result["Waiting"]["ListKey"]
    return _poll_for_results(list_key)


@tool_cache(cache_name)
def superstructure_search(smiles: str, max_records: int = 10) -> Dict[str, Any]:
    """Find larger compounds that contain the query structure.

    Args:
        smiles (str): SMILES string of the query structure
        max_records (int, optional): Maximum number of results (1–100). Defaults to 10.

    Returns:
        Dict[str, Any]: Superstructure search results with larger matching compounds
    """
    endpoint = "/compound/superstructure/smiles/JSON"
    data = {"smiles": smiles}
    params = {"MaxRecords": max_records}

    result = pubchem_client.post(endpoint, params=params, data=data)
    list_key = result["Waiting"]["ListKey"]
    return _poll_for_results(list_key)


@tool_cache(cache_name)
def get_3d_conformers(
    cid: Union[int, str], properties: List[str] = None
) -> Dict[str, Any]:
    """Get 3D conformer data and structural information.

    Args:
        cid (Union[int, str]): PubChem Compound ID (CID)
        properties (List[str], optional): PubChem properties to retrieve. Defaults to 3D conformer properties.

    Returns:
        Dict[str, Any]: 3D conformer data and structural properties
    """
    if properties is None:
        properties = [
            "Volume3D",
            "ConformerCount3D",
            "ConformerModelRMSD3D",
            "FeatureCount3D",
            "FeatureAcceptorCount3D",
            "FeatureDonorCount3D",
            "FeatureAnionCount3D",
            "FeatureCationCount3D",
            "FeatureRingCount3D",
            "FeatureHydrophobeCount3D",
            "EffectiveRotorCount3D",
            "XStericQuadrupole3D",
            "YStericQuadrupole3D",
            "ZStericQuadrupole3D",
        ]
    return get_compound_properties(cid, properties)


@tool_cache(cache_name)
def analyze_stereochemistry(
    cid: Union[int, str], properties: List[str] = None
) -> Dict[str, Any]:
    """Analyze stereochemistry, chirality, and isomer information.

    Args:
        cid (Union[int, str]): PubChem Compound ID (CID)
        properties (List[str], optional): PubChem properties to retrieve. Defaults to stereochemistry properties.

    Returns:
        Dict[str, Any]: Stereochemistry analysis data including atom/bond stereo counts and isotope information
    """
    if properties is None:
        properties = [
            "AtomStereoCount",
            "DefinedAtomStereoCount",
            "UndefinedAtomStereoCount",
            "BondStereoCount",
            "DefinedBondStereoCount",
            "UndefinedBondStereoCount",
            "IsotopeAtomCount",
        ]
    return get_compound_properties(cid, properties)


# helper function to poll for results
def _poll_for_results(
    list_key: str, max_wait_time: int = 30, poll_interval: int = 2
) -> Dict[str, Any]:
    start_time = time.time()
    endpoint = f"/compound/listkey/{list_key}/JSON"

    while True:
        elapsed_time = time.time() - start_time
        if elapsed_time > max_wait_time:
            raise TimeoutError(f"Results not ready after {max_wait_time} seconds")

        result = pubchem_client.get(endpoint)

        if "Waiting" not in result and "Fault" not in result:
            return result

        time.sleep(poll_interval)


# # ==================== Chemical Properties & Descriptors ====================


@tool_cache(cache_name)
def get_compound_properties(
    cid: Union[int, str], properties: List[str] = None
) -> Dict[str, Any]:
    """Get compound properties (MW, logP, TPSA, etc.).

    Args:
        cid (Union[int, str]): PubChem Compound ID (CID)
        properties (List[str], optional): PubChem properties to retrieve. Defaults to common molecular properties.

    Returns:
        Dict[str, Any]: Raw PubChem API response with requested compound properties
    """
    if properties is None:
        properties = [
            "MolecularWeight",
            "XLogP",
            "TPSA",
            "HBondDonorCount",
            "HBondAcceptorCount",
            "RotatableBondCount",
            "Complexity",
            "HeavyAtomCount",
            "Charge",
        ]
    joined_props = ",".join(properties)
    endpoint = f"/compound/cid/{cid}/property/{joined_props}/JSON"
    response = pubchem_client.get(endpoint)
    return response


@tool_cache(cache_name)
def get_pharmacophore_features(
    cid: Union[int, str], properties: List[str] = None
) -> Dict[str, Any]:
    """Get pharmacophore features and binding site information.

    Args:
        cid (Union[int, str]): PubChem Compound ID (CID)
        properties (List[str], optional): Pharmacophore-related PubChem properties to retrieve. Defaults to pharmacophore features.

    Returns:
        Dict[str, Any]: Pharmacophore features and binding site information
    """
    if properties is None:
        properties = [
            "FeatureAcceptorCount3D",
            "FeatureDonorCount3D",
            "FeatureHydrophobeCount3D",
            "FeatureRingCount3D",
            "FeatureCationCount3D",
            "FeatureAnionCount3D",
            "Volume3D",
            "Fingerprint2D",
        ]
    return get_compound_properties(cid, properties)


# # ==================== Bioassay & Activity Data ====================


@tool_cache(cache_name)
def get_bioassay_results(
    cid: Union[int, str], activity_outcome: str = "all", max_records: int = 10
) -> Dict[str, Any]:
    """Get all bioassay results and activities for a compound.

    Args:
        cid (Union[int, str]): PubChem Compound ID (CID)
        activity_outcome (str, optional): Filter by activity outcome. Defaults to "all".
        max_records (int, optional): Maximum number of assay summary entries to return (1–100). Defaults to 10.

    Returns:
        Dict[str, Any]: Raw PubChem API response with bioassay results and activity data
    """
    endpoint = f"/compound/cid/{cid}/assaysummary/JSON"
    response = pubchem_client.get(endpoint, params={"outcome": activity_outcome})
    response["Table"]["Row"] = response["Table"]["Row"][:max_records]
    return response


@tool_cache(cache_name)
def get_bioassay_info(aid: int) -> Dict[str, Any]:
    """Get detailed information for a specific bioassay by AID.

    Args:
        aid (int): PubChem Assay ID (AID)

    Returns:
        Dict[str, Any]: Raw PubChem API response with detailed bioassay information
    """
    response = pubchem_client.get(f"/assay/aid/{aid}/description/JSON")
    return response


# # ==================== PubChem Viewer ====================


@tool_cache(cache_name)
def get_safety_data(cid: Union[int, str]) -> Dict[str, Any]:
    """Get GHS pictograms, signal word, hazard/precaution codes, etc.

    Args:
        cid (Union[int, str]): PubChem Compound ID (CID)

    Returns:
        Dict[str, Any]: Raw PubChem API response with GHS safety classification data
    """
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON"
    response = pubchem_client.client.get(url, params={"heading": "GHS Classification"})
    return response.json()


@tool_cache(cache_name)
def get_toxicity_data(cid: Union[int, str]) -> Dict[str, Any]:
    """Get toxicity information for the compound.

    Args:
        cid (Union[int, str]): PubChem Compound ID (CID)

    Returns:
        Dict[str, Any]: Raw PubChem API response with toxicity information
    """
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON"
    response = pubchem_client.client.get(url, params={"heading": "Toxicity"})
    return response.json()


@tool_cache(cache_name)
def get_drug_medication_data(cid: Union[int, str]) -> Dict[str, Any]:
    """Get drug medication data for the compound.

    Args:
        cid (Union[int, str]): PubChem Compound ID (CID)

    Returns:
        Dict[str, Any]: Raw PubChem API response with drug and medication information
    """
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON"
    response = pubchem_client.client.get(
        url, params={"heading": "Drug and Medication Information"}
    )
    return response.json()


@tool_cache(cache_name)
def get_pharmocology_biochemistry_data(cid: Union[int, str]) -> Dict[str, Any]:
    """Get pharmacology and biochemistry data for the compound.

    Args:
        cid (Union[int, str]): PubChem Compound ID (CID)

    Returns:
        Dict[str, Any]: Raw PubChem API response with pharmacology and biochemistry information
    """
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON"
    response = pubchem_client.client.get(
        url, params={"heading": "Pharmacology and Biochemistry"}
    )
    return response.json()


# ============================ Function List ============================

PUBCHEM_TOOLS = [
    search_pubchem_cid,
    get_compound_info,
    get_compound_synonyms,
    search_similar_compounds,
    substructure_search,
    superstructure_search,
    get_3d_conformers,
    analyze_stereochemistry,
    get_compound_properties,
    get_pharmacophore_features,
    get_bioassay_results,
    get_bioassay_info,
    get_safety_data,
    get_toxicity_data,
    get_drug_medication_data,
    get_pharmocology_biochemistry_data,
]

for i, fn in enumerate(PUBCHEM_TOOLS):
    wrapped = fn  # ai_summarized_output(fn)
    wrapped.__name__ = "PUBCHEM__" + wrapped.__name__
    PUBCHEM_TOOLS[i] = wrapped

if __name__ == "__main__":
    import dotenv

    dotenv.load_dotenv("../../../.env")

    # Test search_pubchem_cid
    print("Testing search_pubchem_cid:")
    result = search_pubchem_cid("Aspirin", limit=5)
    print(result)

    # Test get_compound_info
    print("\nTesting get_compound_info:")
    result = get_compound_info(2244)  # Aspirin CID
    print(result)

    # Test get_compound_synonyms
    print("\nTesting get_compound_synonyms:")
    result = get_compound_synonyms(2244)
    print(result)

    # Test get_compound_properties
    print("\nTesting get_compound_properties:")
    result = get_compound_properties(2244)
    print(result)

    # Test get_bioassay_results
    print("\nTesting get_bioassay_results:")
    result = get_bioassay_results(2244, max_records=5)
    print(result)

    # Test get_safety_data
    print("\nTesting get_safety_data:")
    result = get_safety_data(2244)
    print(result)

    # Test get_toxicity_data
    print("\nTesting get_toxicity_data:")
    result = get_toxicity_data(2244)
    print(result)

    # Test get_drug_medication_data
    print("\nTesting get_drug_medication_data:")
    result = get_drug_medication_data(2244)
    print(result)

    # Test get_pharmocology_biochemistry_data
    print("\nTesting get_pharmocology_biochemistry_data:")
    result = get_pharmocology_biochemistry_data(2244)
    print(result)

    # Note: Some functions like search_similar_compounds, substructure_search, etc. may take longer or require specific inputs
    print(
        "\nOther functions (search_similar_compounds, substructure_search, etc.) are available but not tested here for brevity."
    )
