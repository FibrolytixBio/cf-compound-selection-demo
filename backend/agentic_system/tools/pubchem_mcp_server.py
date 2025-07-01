#!/usr/bin/env python3
"""
PubChem MCP Server - A Model Context Protocol server for chemical data retrieval
"""

import asyncio
import urllib.parse
from typing import List, Optional, Dict, Any, Union

from pydantic import BaseModel, Field
import httpx
from mcp.server.fastmcp import FastMCP

from .tool_utils import mcp_tool_with_prefix


# Create an MCP server
mcp = FastMCP("PubChem MCP Server")
# add server prefix to tool names
mcp.tool = mcp_tool_with_prefix(mcp, "PUBCHEM")

# PubChem API client configuration
PUBCHEM_BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
TIMEOUT = 30.0


class PubChemClient:
    """HTTP client for PubChem API interactions"""

    def __init__(self):
        self.client = httpx.AsyncClient(
            base_url=PUBCHEM_BASE_URL,
            timeout=TIMEOUT,
            headers={
                "User-Agent": "PubChem-MCP-Server/1.0.0",
                "Accept": "application/json",
            },
        )

    async def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make GET request to PubChem API"""
        response = await self.client.get(endpoint, params=params)
        response.raise_for_status()
        return response.json()

    async def post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make POST request to PubChem API"""
        response = await self.client.post(endpoint, json=data)
        response.raise_for_status()
        return response.json()


# Initialize the PubChem client
pubchem_client = PubChemClient()


# ==================== Chemical Search & Retrieval ====================


class SearchCompoundsRequest(BaseModel):
    query: str = Field(
        description="Compound name, CAS number, molecular formula, or chemical identifier"
    )
    search_type: str = Field(
        default="name",
        description="Type of search to perform. Valid options: name, smiles, inchi, sdf, cid, formula",
    )
    max_records: int = Field(
        default=10,
        description="Maximum number of results to return (1–10000)",
        ge=1,
        le=100,
    )


@mcp.tool()
async def search_compounds(request: SearchCompoundsRequest) -> Dict[str, Any]:
    """Search PubChem for compounds and return summary information."""
    endpoint = (
        f"/compound/{request.search_type}/{urllib.parse.quote(request.query)}/cids/JSON"
    )
    res = await pubchem_client.get(endpoint, params={"MaxRecords": request.max_records})
    cids = res.get("IdentifierList", {}).get("CID", [])

    props_ep = (
        f"/compound/cid/{','.join(map(str, cids[:10]))}/property/"
        "MolecularFormula,MolecularWeight,CanonicalSMILES,IUPACName/JSON"
    )
    details = await pubchem_client.get(props_ep)

    return {
        "query": request.query,
        "search_type": request.search_type,
        "total_found": len(cids),
        "details": details,
    }


class CompoundInfoRequest(BaseModel):
    cid: Union[int, str] = Field(
        description="PubChem Compound ID (CID) to retrieve information for"
    )
    format: str = Field(
        default="json", description="Output format to return (e.g., json, xml, etc.)"
    )


@mcp.tool()
async def get_compound_info(request: CompoundInfoRequest) -> Dict[str, Any]:
    """Retrieve detailed information for a specific compound by PubChem CID"""
    response = await pubchem_client.get(
        f"/compound/cid/{request.cid}/{request.format.upper()}"
    )
    return response


class SearchBySmilesRequest(BaseModel):
    smiles: str = Field(description="SMILES string of the query molecule")


@mcp.tool()
async def search_by_smiles(request: SearchBySmilesRequest) -> Dict[str, Any]:
    """Search for compounds by SMILES string (exact match)"""
    endpoint = f"/compound/smiles/{urllib.parse.quote(request.smiles)}/cids/JSON"
    response = await pubchem_client.get(endpoint)

    cid = response["IdentifierList"]["CID"][0]
    details_endpoint = f"/compound/cid/{cid}/property/MolecularFormula,MolecularWeight,CanonicalSMILES,IUPACName/JSON"
    details_response = await pubchem_client.get(details_endpoint)

    return {
        "query_smiles": request.smiles,
        "found_cid": cid,
        "details": details_response,
    }


class SearchByInchiRequest(BaseModel):
    inchi: str = Field(description="InChI string or InChI key")


@mcp.tool()
async def search_by_inchi(request: SearchByInchiRequest) -> Dict[str, Any]:
    """Search for compounds by InChI or InChI key"""
    if request.inchi.startswith("InChI="):
        endpoint = f"/compound/inchi/{urllib.parse.quote(request.inchi)}/cids/JSON"
    else:
        endpoint = f"/compound/inchikey/{urllib.parse.quote(request.inchi)}/cids/JSON"

    res = await pubchem_client.get(endpoint)
    cids = res.get("IdentifierList", {}).get("CID", [])

    cid = cids[0]
    details_ep = (
        f"/compound/cid/{cid}/property/"
        "MolecularFormula,MolecularWeight,CanonicalSMILES,IUPACName/JSON"
    )
    details = await pubchem_client.get(details_ep)
    return {"query_inchi": request.inchi, "found_cid": cid, "details": details}


class SearchByCASRequest(BaseModel):
    cas_number: str = Field(description="CAS Registry Number (e.g., 50-78-2)")


@mcp.tool()
async def search_by_cas_number(request: SearchByCASRequest) -> Dict[str, Any]:
    """Search for compounds by CAS Registry Number"""
    endpoint = f"/compound/name/{urllib.parse.quote(request.cas_number)}/cids/JSON"
    res = await pubchem_client.get(endpoint)
    cids = res.get("IdentifierList", {}).get("CID", [])

    cid = cids[0]
    details_ep = (
        f"/compound/cid/{cid}/property/"
        "MolecularFormula,MolecularWeight,CanonicalSMILES,IUPACName/JSON"
    )
    details = await pubchem_client.get(details_ep)
    return {"cas_number": request.cas_number, "found_cid": cid, "details": details}


class CompoundCIDRequest(BaseModel):
    cid: Union[int, str] = Field(description="PubChem Compound ID (CID)")


@mcp.tool()
async def get_compound_synonyms(request: CompoundCIDRequest) -> Dict[str, Any]:
    """Get all names and synonyms for a compound"""
    endpoint = f"/compound/cid/{request.cid}/synonyms/JSON"
    response = await pubchem_client.get(endpoint)
    return response


# # ==================== Structure Analysis & Similarity ====================


class SearchSimilarCompoundsRequest(BaseModel):
    smiles: str = Field(description="SMILES string of the query molecule")
    threshold: int = Field(
        default=90, ge=0, le=100, description="Similarity threshold (0–100)"
    )
    max_records: int = Field(
        default=10, ge=1, le=100, description="Maximum number of results"
    )


@mcp.tool()
async def search_similar_compounds(
    request: SearchSimilarCompoundsRequest,
) -> Dict[str, Any]:
    """Find chemically similar compounds using Tanimoto similarity."""
    endpoint = "/compound/similarity/smiles/JSON"
    params = {"Threshold": request.threshold, "MaxRecords": request.max_records}
    data = {"smiles": request.smiles}

    response = await pubchem_client.client.post(endpoint, params=params, data=data)
    result = response.json()
    list_key = result["Waiting"]["ListKey"]
    return await _poll_for_results(list_key)


class SubstructureSearchRequest(BaseModel):
    smiles: str = Field(description="SMILES string of the substructure query")
    max_records: int = Field(
        default=10, ge=1, le=10000, description="Maximum number of results"
    )


@mcp.tool()
async def substructure_search(request: SubstructureSearchRequest) -> Dict[str, Any]:
    """Find compounds containing a specific substructure"""
    endpoint = "/compound/substructure/smiles/JSON"
    data = {"smiles": request.smiles}
    params = {"MaxRecords": request.max_records}

    response = await pubchem_client.client.post(endpoint, params=params, data=data)
    result = response.json()
    list_key = result["Waiting"]["ListKey"]
    return await _poll_for_results(list_key)


class SuperstructureSearchRequest(BaseModel):
    smiles: str = Field(description="SMILES string of the query structure")
    max_records: int = Field(
        default=10, ge=1, le=100, description="Maximum number of results"
    )


@mcp.tool()
async def superstructure_search(request: SuperstructureSearchRequest) -> Dict[str, Any]:
    """Find larger compounds that contain the query structure"""
    endpoint = "/compound/superstructure/smiles/JSON"
    data = {"smiles": request.smiles}
    params = {"MaxRecords": request.max_records}

    response = await pubchem_client.client.post(endpoint, params=params, data=data)
    result = response.json()
    list_key = result["Waiting"]["ListKey"]
    return await _poll_for_results(list_key)


class Get3DConformersRequest(BaseModel):
    cid: Union[int, str] = Field(description="PubChem Compound ID (CID)")
    properties: List[str] = Field(
        default=[
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
        ],
        description="PubChem properties to retrieve",
    )


@mcp.tool()
async def get_3d_conformers(request: Get3DConformersRequest) -> Dict[str, Any]:
    """Get 3D conformer data and structural information"""
    return await get_compound_properties(request.cid, request.properties)


class AnalyzeStereochemistryRequest(BaseModel):
    cid: Union[int, str] = Field(description="PubChem Compound ID (CID)")
    properties: List[str] = Field(
        default=[
            "AtomStereoCount",
            "DefinedAtomStereoCount",
            "UndefinedAtomStereoCount",
            "BondStereoCount",
            "DefinedBondStereoCount",
            "UndefinedBondStereoCount",
            "IsotopeAtomCount",
        ],
        description="PubChem properties to retrieve",
    )


@mcp.tool()
async def analyze_stereochemistry(
    request: AnalyzeStereochemistryRequest,
) -> Dict[str, Any]:
    """Analyze stereochemistry, chirality, and isomer information"""
    return await get_compound_properties(request.cid, request.properties)


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


class CompoundPropertiesRequest(BaseModel):
    cid: Union[int, str] = Field(description="PubChem Compound ID (CID)")
    properties: List[str] = Field(
        default=[
            "MolecularWeight",
            "XLogP",
            "TPSA",
            "HBondDonorCount",
            "HBondAcceptorCount",
            "RotatableBondCount",
            "Complexity",
            "HeavyAtomCount",
            "Charge",
        ],
        description="PubChem properties to retrieve",
    )


@mcp.tool()
async def get_compound_properties(request: CompoundPropertiesRequest) -> Dict[str, Any]:
    """Get compound properties (MW, logP, TPSA, etc.)"""
    joined_props = ",".join(request.properties)
    endpoint = f"/compound/cid/{request.cid}/property/{joined_props}/JSON"
    response = await pubchem_client.get(endpoint)
    return response


class PharmacophoreFeaturesRequest(BaseModel):
    cid: Union[int, str] = Field(description="PubChem Compound ID (CID)")
    properties: List[str] = Field(
        default=[
            "FeatureAcceptorCount3D",
            "FeatureDonorCount3D",
            "FeatureHydrophobeCount3D",
            "FeatureRingCount3D",
            "FeatureCationCount3D",
            "FeatureAnionCount3D",
            "Volume3D",
            "Fingerprint2D",
        ],
        description="Pharmacophore-related PubChem properties to retrieve",
    )


@mcp.tool()
async def get_pharmacophore_features(
    request: PharmacophoreFeaturesRequest,
) -> Dict[str, Any]:
    """Get pharmacophore features and binding site information"""
    return await get_compound_properties(request.cid, request.properties)


# # ==================== Bioassay & Activity Data ====================


class BioassayResultsRequest(BaseModel):
    cid: Union[int, str] = Field(description="PubChem Compound ID (CID)")
    activity_outcome: str = Field(
        default="all", description="Filter by activity outcome"
    )
    max_records: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of assay summary entries to return",
    )


@mcp.tool()
async def get_bioassay_results(request: BioassayResultsRequest) -> Dict[str, Any]:
    """Get all bioassay results and activities for a compound"""
    endpoint = f"/compound/cid/{request.cid}/assaysummary/JSON"
    response = await pubchem_client.get(
        endpoint, params={"outcome": request.activity_outcome}
    )
    response["Table"]["Row"] = response["Table"]["Row"][: request.max_records]
    return response


class BioassayInfoRequest(BaseModel):
    aid: int = Field(description="PubChem Assay ID (AID)")


@mcp.tool()
async def get_bioassay_info(request: BioassayInfoRequest) -> Dict[str, Any]:
    """Get detailed information for a specific bioassay by AID"""
    response = await pubchem_client.get(f"/assay/aid/{request.aid}/description/JSON")
    return response


# # ==================== PubChem Viewer ====================


class CompoundViewerRequest(BaseModel):
    cid: Union[int, str] = Field(description="PubChem Compound ID (CID)")


@mcp.tool()
async def get_safety_data(request: CompoundViewerRequest) -> Dict[str, Any]:
    """Get GHS pictograms, signal word, hazard/precaution codes, etc."""
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{request.cid}/JSON"
    response = await pubchem_client.client.get(
        url, params={"heading": "GHS Classification"}
    )
    return response.json()


@mcp.tool()
async def get_toxicity_data(request: CompoundViewerRequest) -> Dict[str, Any]:
    """Get toxicity information for the compound"""
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{request.cid}/JSON"
    response = await pubchem_client.client.get(url, params={"heading": "Toxicity"})
    return response.json()


@mcp.tool()
async def get_drug_medication_data(request: CompoundViewerRequest) -> Dict[str, Any]:
    """Get drug medication data for the compound"""
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{request.cid}/JSON"
    response = await pubchem_client.client.get(
        url, params={"heading": "Drug and Medication Information"}
    )
    return response.json()


@mcp.tool()
async def get_pharmocology_biochemistry_data(
    request: CompoundViewerRequest,
) -> Dict[str, Any]:
    """Get pharmacology and biochemistry data for the compound"""
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{request.cid}/JSON"
    response = await pubchem_client.client.get(
        url, params={"heading": "Pharmacology and Biochemistry"}
    )
    return response.json()


if __name__ == "__main__":
    mcp.run()
