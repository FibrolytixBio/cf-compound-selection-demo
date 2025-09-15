#!/usr/bin/env python3
"""
PubChem Standalone Tools - Synchronous functions with natural language outputs
"""

from typing import Dict, Any, Union, List
import urllib.parse
import asyncio

import httpx
from agentic_system.tools.tool_utils import FileBasedRateLimiter
from agentic_system.tools.tool_utils import tool_cache


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
async def get_compound_info(
    cid: Union[int, str], format: str = "json"
) -> Dict[str, Any]:
    """Retrieve detailed information for a specific compound by PubChem CID.

    Args:
        cid (Union[int, str]): PubChem Compound ID (CID) to retrieve information for
        format (str, optional): Output format to return (e.g., json, xml, etc.). Defaults to "json".

    Returns:
        Dict[str, Any]: Raw PubChem API response with detailed compound information
    """
    response = await pubchem_client.get(f"/compound/cid/{cid}/{format.upper()}")
    return response


@tool_cache(cache_name)
async def search_by_smiles(smiles: str) -> Dict[str, Any]:
    """Search for compounds by SMILES string (exact match).

    Args:
        smiles (str): SMILES string of the query molecule

    Returns:
        Dict[str, Any]: Search results with query SMILES, found CID, and compound details
    """
    endpoint = f"/compound/smiles/{urllib.parse.quote(smiles)}/cids/JSON"
    response = await pubchem_client.get(endpoint)

    cid = response["IdentifierList"]["CID"][0]
    details_endpoint = f"/compound/cid/{cid}/property/MolecularFormula,MolecularWeight,CanonicalSMILES,IUPACName/JSON"
    details_response = await pubchem_client.get(details_endpoint)

    return {
        "query_smiles": smiles,
        "found_cid": cid,
        "details": details_response,
    }


@tool_cache(cache_name)
async def search_by_inchi(inchi: str) -> Dict[str, Any]:
    """Search for compounds by InChI or InChI key.

    Args:
        inchi (str): InChI string or InChI key

    Returns:
        Dict[str, Any]: Search results with query InChI, found CID, and compound details
    """
    if inchi.startswith("InChI="):
        endpoint = f"/compound/inchi/{urllib.parse.quote(inchi)}/cids/JSON"
    else:
        endpoint = f"/compound/inchikey/{urllib.parse.quote(inchi)}/cids/JSON"

    res = await pubchem_client.get(endpoint)
    cids = res.get("IdentifierList", {}).get("CID", [])

    cid = cids[0]
    details_ep = (
        f"/compound/cid/{cid}/property/"
        "MolecularFormula,MolecularWeight,CanonicalSMILES,IUPACName/JSON"
    )
    details = await pubchem_client.get(details_ep)
    return {"query_inchi": inchi, "found_cid": cid, "details": details}


@tool_cache(cache_name)
async def search_by_cas_number(cas_number: str) -> Dict[str, Any]:
    """Search for compounds by CAS Registry Number.

    Args:
        cas_number (str): CAS Registry Number (e.g., 50-78-2)

    Returns:
        Dict[str, Any]: Search results with CAS number, found CID, and compound details
    """
    endpoint = f"/compound/name/{urllib.parse.quote(cas_number)}/cids/JSON"
    res = await pubchem_client.get(endpoint)
    cids = res.get("IdentifierList", {}).get("CID", [])

    cid = cids[0]
    details_ep = (
        f"/compound/cid/{cid}/property/"
        "MolecularFormula,MolecularWeight,CanonicalSMILES,IUPACName/JSON"
    )
    details = await pubchem_client.get(details_ep)
    return {"cas_number": cas_number, "found_cid": cid, "details": details}


@tool_cache(cache_name)
async def get_compound_synonyms(cid: Union[int, str]) -> Dict[str, Any]:
    """Get all names and synonyms for a compound.

    Args:
        cid (Union[int, str]): PubChem Compound ID (CID)

    Returns:
        Dict[str, Any]: Raw PubChem API response with compound synonyms and names
    """
    endpoint = f"/compound/cid/{cid}/synonyms/JSON"
    response = await pubchem_client.get(endpoint)
    return response


# # ==================== Structure Analysis & Similarity ====================


@tool_cache(cache_name)
async def search_similar_compounds(
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

    response = await pubchem_client.client.post(endpoint, params=params, data=data)
    result = response.json()
    list_key = result["Waiting"]["ListKey"]
    return await _poll_for_results(list_key)


@tool_cache(cache_name)
async def substructure_search(smiles: str, max_records: int = 10) -> Dict[str, Any]:
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

    response = await pubchem_client.client.post(endpoint, params=params, data=data)
    result = response.json()
    list_key = result["Waiting"]["ListKey"]
    return await _poll_for_results(list_key)


@tool_cache(cache_name)
async def superstructure_search(smiles: str, max_records: int = 10) -> Dict[str, Any]:
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

    response = await pubchem_client.client.post(endpoint, params=params, data=data)
    result = response.json()
    list_key = result["Waiting"]["ListKey"]
    return await _poll_for_results(list_key)


@tool_cache(cache_name)
async def get_3d_conformers(
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
    return await get_compound_properties(cid, properties)


@tool_cache(cache_name)
async def analyze_stereochemistry(
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
    return await get_compound_properties(cid, properties)


# helper function to poll for results
async def _poll_for_results(
    list_key: str, max_wait_time: int = 30, poll_interval: int = 2
) -> Dict[str, Any]:
    start_time = asyncio.get_event_loop().time()
    endpoint = f"/compound/listkey/{list_key}/JSON"

    while True:
        elapsed_time = asyncio.get_event_loop().time() - start_time
        if elapsed_time > max_wait_time:
            raise TimeoutError(f"Results not ready after {max_wait_time} seconds")

        response = await pubchem_client.client.get(endpoint)
        result = response.json()

        if "Waiting" not in result and "Fault" not in result:
            return result

        await asyncio.sleep(poll_interval)


# # ==================== Chemical Properties & Descriptors ====================


@tool_cache(cache_name)
async def get_compound_properties(
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
    response = await pubchem_client.get(endpoint)
    return response


@tool_cache(cache_name)
async def get_pharmacophore_features(
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
    return await get_compound_properties(cid, properties)


# # ==================== Bioassay & Activity Data ====================


@tool_cache(cache_name)
async def get_bioassay_results(
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
    response = await pubchem_client.get(endpoint, params={"outcome": activity_outcome})
    response["Table"]["Row"] = response["Table"]["Row"][:max_records]
    return response


@tool_cache(cache_name)
async def get_bioassay_info(aid: int) -> Dict[str, Any]:
    """Get detailed information for a specific bioassay by AID.

    Args:
        aid (int): PubChem Assay ID (AID)

    Returns:
        Dict[str, Any]: Raw PubChem API response with detailed bioassay information
    """
    response = await pubchem_client.get(f"/assay/aid/{aid}/description/JSON")
    return response


# # ==================== PubChem Viewer ====================


@tool_cache(cache_name)
async def get_safety_data(cid: Union[int, str]) -> Dict[str, Any]:
    """Get GHS pictograms, signal word, hazard/precaution codes, etc.

    Args:
        cid (Union[int, str]): PubChem Compound ID (CID)

    Returns:
        Dict[str, Any]: Raw PubChem API response with GHS safety classification data
    """
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON"
    response = await pubchem_client.client.get(
        url, params={"heading": "GHS Classification"}
    )
    return response.json()


@tool_cache(cache_name)
async def get_toxicity_data(cid: Union[int, str]) -> Dict[str, Any]:
    """Get toxicity information for the compound.

    Args:
        cid (Union[int, str]): PubChem Compound ID (CID)

    Returns:
        Dict[str, Any]: Raw PubChem API response with toxicity information
    """
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON"
    response = await pubchem_client.client.get(url, params={"heading": "Toxicity"})
    return response.json()


@tool_cache(cache_name)
async def get_drug_medication_data(cid: Union[int, str]) -> Dict[str, Any]:
    """Get drug medication data for the compound.

    Args:
        cid (Union[int, str]): PubChem Compound ID (CID)

    Returns:
        Dict[str, Any]: Raw PubChem API response with drug and medication information
    """
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON"
    response = await pubchem_client.client.get(
        url, params={"heading": "Drug and Medication Information"}
    )
    return response.json()


@tool_cache(cache_name)
async def get_pharmocology_biochemistry_data(cid: Union[int, str]) -> Dict[str, Any]:
    """Get pharmacology and biochemistry data for the compound.

    Args:
        cid (Union[int, str]): PubChem Compound ID (CID)

    Returns:
        Dict[str, Any]: Raw PubChem API response with pharmacology and biochemistry information
    """
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON"
    response = await pubchem_client.client.get(
        url, params={"heading": "Pharmacology and Biochemistry"}
    )
    return response.json()


# ============================ Function List ============================

PUBCHEM_TOOLS = [search_pubchem_cid]

for tool in PUBCHEM_TOOLS:
    tool.__name__ = "CHEMBL__" + tool.__name__

if __name__ == "__main__":
    import dotenv
    import asyncio

    dotenv.load_dotenv("../../../.env")

    # Example usage of the PubChem tools
    result = search_pubchem_cid("Aspirin", limit=5)
    print(result)
