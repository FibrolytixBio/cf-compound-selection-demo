#!/usr/bin/env python3
"""
PubChem Standalone Tools - Synchronous functions with natural language outputs
"""

from typing import Optional, Dict, Any, Union, List
import time
import urllib.parse

import httpx
from pydantic import BaseModel, Field


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

    def get(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make GET request to PubChem API"""
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
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make POST request to PubChem API"""
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


# ==================== Compound Search & ID Tools ====================


class SearchCompoundsRequest(BaseModel):
    query: str = Field(
        description="Compound name, CAS number, or molecular formula to search for"
    )
    limit: int = Field(
        default=5, ge=1, le=10, description="Number of results to return (1-10)"
    )


def search_pubchem_cid(request: SearchCompoundsRequest) -> str:
    """Search for PubChem CIDs by compound name, CAS number, or formula. Returns CIDs and key names."""
    endpoint = f"/compound/name/{urllib.parse.quote(request.query)}/cids/JSON"
    result = pubchem_client.get(endpoint, params={"MaxRecords": request.limit})

    if "error" in result:
        return f"Error searching for compound: {result['error']}"

    cids: List[int] = result.get("IdentifierList", {}).get("CID", [])
    if not cids:
        return f"No compounds found matching '{request.query}'"

    # If single CID, enrich with IUPAC name; if many, just list CIDs
    if len(cids) == 1:
        props_endpoint = f"/compound/cid/{cids[0]}/property/IUPACName/JSON"
        props_result = pubchem_client.get(props_endpoint)
        if "error" not in props_result and props_result.get("PropertyTable"):
            name = props_result["PropertyTable"]["Properties"][0].get("IUPACName", "")
            return f"Found PubChem CID {cids[0]} ({name}) for '{request.query}'"

    return (
        f"Found {min(len(cids), request.limit)} compound(s) matching '{request.query}': CIDs "
        + "\n - ".join(map(str, cids[: request.limit]))
    )


class CIDPropertiesRequest(BaseModel):
    cid: Union[int, str] = Field(description="PubChem Compound ID (CID)")


def get_cid_properties(request: CIDPropertiesRequest) -> str:
    """Get key physicochemical properties for a PubChem compound that are relevant for drug discovery."""
    properties = [
        "MolecularFormula",
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

    endpoint = f"/compound/cid/{request.cid}/property/{','.join(properties)}/JSON"
    result = pubchem_client.get(endpoint)

    if "error" in result:
        return f"Error retrieving properties: {result['error']}"

    props_table = result.get("PropertyTable", {}).get("Properties", [])
    if not props_table:
        return f"No properties found for CID {request.cid}"

    props = props_table[0]

    # Build natural language summary
    summary_parts: List[str] = [f"Properties of PubChem CID {request.cid}:"]

    # Basic info
    formula = props.get("MolecularFormula")
    mw = props.get("MolecularWeight")
    if formula and mw:
        try:
            summary_parts.append(
                f"molecular formula {formula} with MW {float(mw):.2f} g/mol"
            )
        except Exception:
            summary_parts.append(f"molecular formula {formula} with MW {mw} g/mol")

    # Lipophilicity
    xlogp = props.get("XLogP")
    if xlogp is not None:
        try:
            x = float(xlogp)
            if x < 0:
                lip = "hydrophilic"
            elif x > 3:
                lip = "lipophilic"
            else:
                lip = "moderate lipophilicity"
            summary_parts.append(f"XLogP {x:.2f} ({lip})")
        except Exception:
            summary_parts.append(f"XLogP {xlogp}")

    # Permeability (TPSA)
    tpsa = props.get("TPSA")
    if tpsa is not None:
        try:
            t = float(tpsa)
            perm = "good" if t < 90 else ("moderate" if t < 140 else "poor")
            summary_parts.append(f"TPSA {t:.1f} Å² ({perm} permeability expected)")
        except Exception:
            summary_parts.append(f"TPSA {tpsa} Å²")

    # H-bonding
    hbd = props.get("HBondDonorCount")
    hba = props.get("HBondAcceptorCount")
    if hbd is not None and hba is not None:
        summary_parts.append(f"{hbd} H-bond donors and {hba} H-bond acceptors")

    # Flexibility
    rtb = props.get("RotatableBondCount")
    if rtb is not None:
        try:
            r = int(rtb)
        except Exception:
            r = None
        if r is not None:
            flex = (
                "rigid"
                if r <= 3
                else ("flexible" if r >= 7 else "moderate flexibility")
            )
            summary_parts.append(f"{r} rotatable bonds ({flex})")
        else:
            summary_parts.append(f"Rotatable bonds: {rtb}")

    # Complexity
    complexity = props.get("Complexity")
    if complexity is not None:
        try:
            c = float(complexity)
            desc = (
                "simple"
                if c < 250
                else ("complex" if c > 500 else "moderate complexity")
            )
            summary_parts.append(f"molecular complexity {c:.0f} ({desc})")
        except Exception:
            summary_parts.append(f"molecular complexity {complexity}")

    # Charge
    charge = props.get("Charge")
    if charge is not None:
        try:
            ch = int(charge)
            if ch != 0:
                charge_type = "cationic" if ch > 0 else "anionic"
                summary_parts.append(f"formal charge {ch:+d} ({charge_type})")
        except Exception:
            pass

    return ". ".join(summary_parts) + "."


# ==================== Bioassay & Activity Tools ====================


class BioassayResultsRequest(BaseModel):
    cid: Union[int, str] = Field(description="PubChem Compound ID (CID)")
    max_assays: int = Field(
        default=5, ge=1, le=100, description="Maximum number of bioassays to summarize"
    )


def get_bioassay_summary(request: BioassayResultsRequest) -> str:
    """Get a summary of bioassay results for a compound, focusing on the most relevant therapeutic activities."""
    endpoint = f"/compound/cid/{request.cid}/assaysummary/JSON"
    result = pubchem_client.get(endpoint)

    if "error" in result:
        return f"Error retrieving bioassay data: {result['error']}"

    table = result.get("Table", {})
    rows: List[Dict[str, Any]] = table.get("Row", [])

    if not rows:
        return f"No bioassay data found for CID {request.cid}"

    columns: List[str] = table.get("Columns", {}).get("Column", [])

    active_assays: List[Dict[str, Any]] = []
    inactive_assays: List[Dict[str, Any]] = []
    inconclusive_assays: List[Dict[str, Any]] = []

    for row in rows:
        assay_data: Dict[str, Any] = {}
        cells = row.get("Cell", [])
        for i, cell in enumerate(cells):
            if i < len(columns):
                col_name = columns[i]
                assay_data[col_name] = cell
        outcome = str(assay_data.get("Activity Outcome", ""))
        if "Active" in outcome:
            active_assays.append(assay_data)
        elif "Inactive" in outcome:
            inactive_assays.append(assay_data)
        else:
            inconclusive_assays.append(assay_data)

    # Build summary
    summary_parts = [
        f"Bioassay summary for CID {request.cid}:",
        f"Tested in {len(rows)} assays - {len(active_assays)} active, {len(inactive_assays)} inactive",
    ]

    if active_assays:
        summary_parts.append("\nActive in:")
        for assay in active_assays[: request.max_assays]:
            aid = assay.get("AID", "Unknown")
            name = assay.get("Assay Name", "Unknown assay")
            name = name if len(name) <= 100 else name[:97] + "..."
            summary_parts.append(f"• AID {aid}: {name} \n")

    if len(active_assays) > request.max_assays:
        summary_parts.append(
            f"(Showing {request.max_assays} of {len(active_assays)} active assays)"
        )

    return "\n".join(summary_parts)


# ==================== Safety & Drug Information Tools ====================


class SafetyDataRequest(BaseModel):
    cid: Union[int, str] = Field(description="PubChem Compound ID (CID)")


def get_safety_summary(request: SafetyDataRequest) -> str:
    """Get safety information including GHS classification and hazard warnings for a compound."""
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{request.cid}/JSON"
    try:
        response = pubchem_client.client.get(
            url, params={"heading": "GHS Classification"}
        )
        response.raise_for_status()
    except httpx.HTTPError:
        return f"No safety data available for CID {request.cid}"

    try:
        data = response.json()
        sections = data.get("Record", {}).get("Section", [])
        if not sections:
            return f"No GHS safety classification found for CID {request.cid}"

        summary_parts: List[str] = [f"Safety information for CID {request.cid}:"]

        for section in sections:
            if section.get("TOCHeading") == "GHS Classification":
                for subsection in section.get("Section", []):
                    for info in subsection.get("Information", []):
                        value = info.get("Value", {})
                        name = info.get("Name", "")

                        # Pictograms
                        if "Pictogram" in str(value):
                            pictograms: List[str] = []
                            for item in value.get("StringWithMarkup", []):
                                s = item.get("String")
                                if s:
                                    pictograms.append(s)
                            if pictograms:
                                summary_parts.append(
                                    f"GHS Pictograms: {', '.join(pictograms)}"
                                )

                        # Signal word
                        elif "Signal" in str(value):
                            signal = value.get("StringWithMarkup", [{}])[0].get(
                                "String", ""
                            )
                            if signal:
                                summary_parts.append(f"Signal word: {signal}")

                        # Hazard statements
                        elif "Hazard Statement" in name:
                            hazards: List[str] = []
                            for item in value.get("StringWithMarkup", []):
                                s = item.get("String")
                                if s:
                                    hazards.append(s)
                            if hazards:
                                summary_parts.append(
                                    f"Hazard statements: {'; '.join(hazards[:3])}"
                                )
                                if len(hazards) > 3:
                                    summary_parts.append(
                                        f"  (and {len(hazards) - 3} more)"
                                    )

        if len(summary_parts) == 1:
            return f"Limited safety data available for CID {request.cid}"

        return "\n".join(summary_parts)

    except Exception as e:
        return f"Error parsing safety data for CID {request.cid}: {str(e)}"


class DrugDataRequest(BaseModel):
    cid: Union[int, str] = Field(description="PubChem Compound ID (CID)")


def get_drug_summary(request: DrugDataRequest) -> str:
    """Get drug and medication information for a compound including therapeutic uses and pharmacology."""
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{request.cid}/JSON"
    try:
        response = pubchem_client.client.get(
            url, params={"heading": "Drug and Medication Information"}
        )
        response.raise_for_status()
    except httpx.HTTPError:
        return f"No drug information available for CID {request.cid}"

    try:
        data = response.json()
        sections = data.get("Record", {}).get("Section", [])
        if not sections:
            return f"No drug/medication data found for CID {request.cid}"

        summary_parts: List[str] = [f"Drug information for CID {request.cid}:"]

        for section in sections:
            for subsection in section.get("Section", []):
                heading = subsection.get("TOCHeading", "")

                # Therapeutic uses
                if "Therapeutic Use" in heading:
                    uses: List[str] = []
                    for info in subsection.get("Information", []):
                        value = info.get("Value", {})
                        for item in (
                            value.get("StringWithMarkup", [])
                            if isinstance(value, dict)
                            else []
                        ):
                            s = item.get("String")
                            if s:
                                uses.append(s)
                    if uses:
                        summary_parts.append(f"Therapeutic uses: {', '.join(uses[:3])}")
                        if len(uses) > 3:
                            summary_parts.append(f"  (and {len(uses) - 3} more)")

                # Drug classes
                elif "Drug Class" in heading:
                    classes: List[str] = []
                    for info in subsection.get("Information", []):
                        value = info.get("Value", {})
                        for item in (
                            value.get("StringWithMarkup", [])
                            if isinstance(value, dict)
                            else []
                        ):
                            s = item.get("String")
                            if s:
                                classes.append(s)
                    if classes:
                        summary_parts.append(f"Drug classes: {', '.join(classes[:2])}")

                # FDA status lines
                elif "FDA" in heading:
                    for info in subsection.get("Information", []):
                        name = info.get("Name", "")
                        value = info.get("Value", {})
                        value_str = ""
                        if isinstance(value, dict) and value.get("StringWithMarkup"):
                            value_str = value["StringWithMarkup"][0].get("String", "")
                        if value_str and "FDA" in name:
                            summary_parts.append(f"{name}: {value_str}")

        if len(summary_parts) == 1:
            return f"CID {request.cid} - no specific drug/medication information available (may not be an approved drug)"

        return "\n".join(summary_parts)

    except Exception as e:
        return f"Error parsing drug data for CID {request.cid}: {str(e)}"


# ==================== Structure Similarity Tools ====================


class SimilaritySearchRequest(BaseModel):
    cid: Union[int, str] = Field(description="PubChem CID of the query compound")
    threshold: int = Field(
        default=90,
        ge=80,
        le=100,
        description="Similarity threshold percentage (80-100)",
    )
    max_results: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum number of similar compounds to return",
    )


def _poll_for_results(
    list_key: str, max_wait_time: int = 30, poll_interval: int = 2
) -> Dict[str, Any]:
    """Poll PubChem for asynchronous search results (synchronous waiter)."""
    endpoint = f"/compound/listkey/{list_key}/JSON"
    elapsed = 0
    while elapsed < max_wait_time:
        time.sleep(poll_interval)
        elapsed += poll_interval
        response = pubchem_client.client.get(endpoint)
        if response.status_code == 200:
            result = response.json()
            if "Waiting" not in result and "Fault" not in result:
                return result
    return {"error": f"Search timed out after {max_wait_time} seconds"}


def find_similar_compounds(request: SimilaritySearchRequest) -> str:
    """Find compounds similar to a given CID, useful for scaffold hopping and analog identification."""
    # Fetch SMILES for the query CID
    props_endpoint = f"/compound/cid/{request.cid}/property/CanonicalSMILES/JSON"
    props_result = pubchem_client.get(props_endpoint)
    if "error" in props_result:
        return (
            f"Error retrieving structure for CID {request.cid}: {props_result['error']}"
        )

    smiles = (
        props_result.get("PropertyTable", {})
        .get("Properties", [{}])[0]
        .get("CanonicalSMILES")
    )
    if not smiles:
        return f"Could not retrieve structure for CID {request.cid}"

    # Submit similarity search
    endpoint = "/compound/similarity/smiles/JSON"
    params = {"Threshold": request.threshold, "MaxRecords": request.max_results * 2}
    post_result = pubchem_client.post(endpoint, params=params, data={"smiles": smiles})

    if "error" in post_result:
        return f"Error searching for similar compounds: {post_result['error']}"

    list_key = post_result.get("Waiting", {}).get("ListKey")
    if not list_key:
        # Sometimes PubChem returns results directly
        found_cids = post_result.get("IdentifierList", {}).get("CID", [])
        if not found_cids:
            return "Error initiating similarity search"
    else:
        # Poll until results ready
        results = _poll_for_results(list_key)
        if not results or "error" in results:
            return f"No similar compounds found for CID {request.cid} at {request.threshold}% similarity"
        found_cids = results.get("IdentifierList", {}).get("CID", [])

    # Filter out self and trim
    similar_cids = [cid for cid in found_cids if str(cid) != str(request.cid)][
        : request.max_results
    ]
    if not similar_cids:
        return f"No similar compounds found for CID {request.cid} at {request.threshold}% similarity threshold"

    # Enrich with names/formulas
    props_endpoint = f"/compound/cid/{','.join(map(str, similar_cids))}/property/IUPACName,MolecularFormula/JSON"
    props_result = pubchem_client.get(props_endpoint)

    summary_parts = [
        f"Found {len(similar_cids)} compounds similar to CID {request.cid} (≥{request.threshold}% Tanimoto):"
    ]

    if "error" not in props_result and props_result.get("PropertyTable"):
        for prop in props_result["PropertyTable"]["Properties"]:
            cid = prop.get("CID")
            name = prop.get("IUPACName", "No name")
            formula = prop.get("MolecularFormula", "")
            if len(name) > 50:
                name = name[:47] + "..."
            summary_parts.append(f"• CID {cid}: {name} ({formula})")
    else:
        summary_parts.extend([f"• CID {cid}" for cid in similar_cids])

    return "\n".join(summary_parts)


# ==================== Function List ====================

PUBCHEM_TOOLS = [
    search_pubchem_cid,
    get_cid_properties,
    get_bioassay_summary,
    get_safety_summary,
    get_drug_summary,
    find_similar_compounds,
]
