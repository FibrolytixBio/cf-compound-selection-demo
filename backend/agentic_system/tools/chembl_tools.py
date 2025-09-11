#!/usr/bin/env python3
"""
ChEMBL Standalone Tools - Synchronous functions with natural language outputs
"""

from typing import Dict, Any
import httpx
from agentic_system.tools.tool_utils import FileBasedRateLimiter
from agentic_system.tools.tool_utils import tool_cache


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
def get_compound_properties(chembl_id: str) -> str:
    """Get key physicochemical properties for a compound that are relevant for drug discovery.

    Args:
        chembl_id (str): ChEMBL ID of the compound (e.g., CHEMBL25)

    Returns:
        str: Natural language summary of compound properties
    """
    result = chembl_client.get(
        "/molecule.json", params={"molecule_chembl_id": chembl_id, "limit": 1}
    )

    if "error" in result:
        return f"Error retrieving properties: {result['error']}"

    molecules = result.get("molecules", [])
    if not molecules:
        return f"No data found for {chembl_id}"

    mol = molecules[0]
    props = mol.get("molecule_properties", {})

    if not props:
        return f"{chembl_id} has no calculated properties available"

    # Build natural language summary
    summary_parts = [f"Properties of {chembl_id}:"]

    # Add key properties with context
    mw = props.get("mw_freebase")
    if mw:
        try:
            mw_float = float(mw)
            summary_parts.append(f"molecular weight {mw_float:.1f} Da")
        except (ValueError, TypeError):
            summary_parts.append(f"molecular weight {mw} Da")

    logp = props.get("alogp")
    if logp is not None:
        try:
            logp_float = float(logp)
            lipophilicity = (
                "hydrophilic"
                if logp_float < 0
                else "lipophilic"
                if logp_float > 3
                else "moderate lipophilicity"
            )
            summary_parts.append(f"ALogP {logp_float:.2f} ({lipophilicity})")
        except (ValueError, TypeError):
            summary_parts.append(f"ALogP {logp}")

    tpsa = props.get("psa")
    if tpsa:
        try:
            tpsa_float = float(tpsa)
            permeability = (
                "good"
                if tpsa_float < 90
                else "moderate"
                if tpsa_float < 140
                else "poor"
            )
            summary_parts.append(
                f"TPSA {tpsa_float:.1f} Ų ({permeability} permeability expected)"
            )
        except (ValueError, TypeError):
            summary_parts.append(f"TPSA {tpsa} Ų")

    hbd = props.get("hbd")
    hba = props.get("hba")
    if hbd is not None and hba is not None:
        summary_parts.append(f"{hbd} H-bond donors and {hba} H-bond acceptors")

    rtb = props.get("rtb")
    if rtb is not None:
        flexibility = (
            "rigid" if rtb <= 3 else "flexible" if rtb >= 7 else "moderate flexibility"
        )
        summary_parts.append(f"{rtb} rotatable bonds ({flexibility})")

    ro5 = props.get("num_ro5_violations")
    if ro5 is not None:
        ro5_text = (
            "compliant with Lipinski's Rule of Five"
            if ro5 == 0
            else f"has {ro5} Ro5 violation(s)"
        )
        summary_parts.append(ro5_text)

    # Add molecular type
    mol_type = mol.get("molecule_type")
    if mol_type:
        summary_parts.append(f"classified as {mol_type}")

    return ". ".join(summary_parts) + "."


@tool_cache(cache_name)
def get_compound_bioactivities_summary(
    chembl_id: str, activity_type: str = None, max_results: int = 5
) -> str:
    """Get a summary of the most relevant bioactivities for a compound, focusing on potency data useful for drug discovery.

    Args:
        chembl_id (str): ChEMBL ID of the compound (e.g., CHEMBL25)
        activity_type (str, optional): Filter by activity type (e.g., IC50, Ki, EC50). Defaults to None.
        max_results (int, optional): Maximum number of activities to summarize (1-10). Defaults to 5.

    Returns:
        str: Natural language summary of compound bioactivities
    """
    params = {
        "molecule_chembl_id": chembl_id,
        "limit": 50,  # Get more initially to summarize better
    }
    if activity_type:
        params["standard_type"] = activity_type

    result = chembl_client.get("/activity.json", params=params)

    if "error" in result:
        return f"Error retrieving bioactivities: {result['error']}"

    activities = result.get("activities", [])
    if not activities:
        return f"No bioactivity data found for {chembl_id}"

    # Group activities by target and summarize
    target_activities = {}
    for act in activities:
        target_name = act.get("target_pref_name", "Unknown target")
        target_id = act.get("target_chembl_id", "")

        if target_name not in target_activities:
            target_activities[target_name] = {"target_id": target_id, "activities": []}

        # Extract key activity data
        if act.get("standard_value") and act.get("standard_type"):
            target_activities[target_name]["activities"].append(
                {
                    "type": act["standard_type"],
                    "value": float(act["standard_value"]),
                    "units": act.get("standard_units", ""),
                    "relation": act.get("standard_relation", "="),
                }
            )

    # Build summary
    summary_parts = [f"Bioactivity summary for {chembl_id}:"]

    count = 0
    for target_name, data in sorted(
        target_activities.items(), key=lambda x: len(x[1]["activities"]), reverse=True
    ):
        if count >= max_results:
            break

        target_id = data["target_id"]
        activities = data["activities"]

        # Get best activity for each type
        activity_summary = []
        for act_type in set(a["type"] for a in activities):
            type_activities = [a for a in activities if a["type"] == act_type]
            best = min(type_activities, key=lambda x: x["value"])

            # Format value with appropriate precision
            if best["value"] < 0.1:
                value_str = f"{best['value']:.2e}"
            elif best["value"] < 1000:
                value_str = f"{best['value']:.1f}"
            else:
                value_str = f"{best['value']:.0f}"

            activity_summary.append(
                f"{best['type']} {best['relation']} {value_str} {best['units']}"
            )

        summary_parts.append(
            f"\n• {target_name} ({target_id}): " + ", ".join(activity_summary)
        )
        count += 1

    if len(target_activities) > max_results:
        summary_parts.append(
            f"(Showing top {max_results} of {len(target_activities)} targets with activity data)"
        )

    return "\n".join(summary_parts)


@tool_cache(cache_name)
def get_drug_info_summary(chembl_id: str) -> str:
    """Get comprehensive drug information including approval status, indications, mechanism of action, and warnings.

    Args:
        chembl_id (str): ChEMBL ID of the compound (e.g., CHEMBL25)

    Returns:
        str: Natural language summary of drug information
    """

    # Gather all relevant drug information
    summaries = []

    # 1. Basic drug info
    drug_result = chembl_client.get(
        "/drug.json", params={"molecule_chembl_id": chembl_id, "limit": 1}
    )

    if "error" not in drug_result and drug_result.get("drugs"):
        drug = drug_result["drugs"][0]
        if drug.get("first_approval"):
            summaries.append(
                f"{chembl_id} is an approved drug (first approved: {drug['first_approval']})"
            )
        else:
            summaries.append(f"{chembl_id} is not an approved drug")
    else:
        summaries.append(f"{chembl_id} is not an approved drug")

    # 2. Mechanism of action
    moa_result = chembl_client.get(
        "/mechanism.json", params={"molecule_chembl_id": chembl_id, "limit": 5}
    )

    if "error" not in moa_result and moa_result.get("mechanisms"):
        mechanisms = moa_result["mechanisms"]
        if mechanisms:
            moa_summaries = []
            for mech in mechanisms:
                moa = mech.get("mechanism_of_action", "")
                action_type = mech.get("action_type", "")
                target_id = mech.get("target_chembl_id", "")
                if moa:
                    summary = f"{moa}"
                    if action_type:
                        summary += f" ({action_type})"
                    if target_id:
                        summary += f" targeting {target_id}"
                    moa_summaries.append(summary)
            if moa_summaries:
                summaries.append("Mechanisms of action: " + "; ".join(moa_summaries))

    # 3. Drug indications
    indication_result = chembl_client.get(
        "/drug_indication.json",
        params={"molecule_chembl_id": chembl_id, "limit": 10},
    )

    if "error" not in indication_result and indication_result.get("drug_indications"):
        indications = indication_result["drug_indications"]
        if indications:
            ind_summaries = []
            for ind in indications:
                term = ind.get("efo_term", "")
                phase = ind.get("max_phase_for_ind", "")
                mesh = ind.get("mesh_heading", "")
                if term:
                    summary = term
                    if phase:
                        summary += f" (Phase {phase})"
                    if mesh and mesh != term:
                        summary += f" ({mesh})"
                    ind_summaries.append(summary)
            if ind_summaries:
                summaries.append("Drug indications: " + ", ".join(ind_summaries))

    # 4. Drug warnings
    warning_result = chembl_client.get(
        "/drug_warning.json",
        params={"molecule_chembl_id": chembl_id, "limit": 5},
    )

    if "error" not in warning_result and warning_result.get("drug_warnings"):
        warnings = warning_result["drug_warnings"]
        if warnings:
            warn_summaries = []
            for warn in warnings:
                warn_type = warn.get("warning_type", "")
                desc = warn.get("warning_description", "")
                if desc:
                    summary = desc
                    if warn_type:
                        summary = f"{warn_type}: {desc}"
                    warn_summaries.append(summary)
            if warn_summaries:
                summaries.append("Drug warnings: " + "; ".join(warn_summaries))

    if not summaries:
        return f"No drug information found for {chembl_id} - this may not be an approved drug or drug candidate"

    return "\n\n".join(summaries)


# ============================ Target Tools =============================


@tool_cache(cache_name)
def search_target_id(query: str, limit: int = 5) -> str:
    """Search for ChEMBL target IDs by name, gene symbol, or UniProt accession. Returns only the target IDs for efficient lookup.

    Args:
        query (str): Target name, gene symbol, or UniProt accession to search for
        limit (int, optional): Number of results to return (1-10). Defaults to 5.

    Returns:
        str: Natural language summary of search results
    """
    params = {
        "q": query,
        "limit": limit,
    }
    result = chembl_client.get("/target/search.json", params=params)

    if "error" in result:
        return f"Error searching for target: {result['error']}"

    targets = result.get("targets", [])
    if not targets:
        return f"No targets found matching '{query}'"

    # Extract target IDs and names
    target_list = []
    for target in targets[:limit]:
        target_id = target.get("target_chembl_id", "Unknown")
        pref_name = target.get("pref_name", "No name")
        organism = target.get("organism", "")

        target_str = f"{target_id} ({pref_name}"
        if organism:
            target_str += f", {organism}"
        target_str += ")"

        target_list.append(target_str)

    return f"Found {len(target_list)} target(s) matching '{query}': " + ", ".join(
        target_list
    )


@tool_cache(cache_name)
def get_target_activities_summary(
    target_chembl_id: str, activity_type: str = "IC50", max_compounds: int = 5
) -> str:
    """Get a summary of the most potent compounds against a target, useful for understanding chemical matter and SAR.

    Args:
        target_chembl_id (str): ChEMBL ID of the target (e.g., CHEMBL204)
        activity_type (str, optional): Activity type to focus on (e.g., IC50, Ki). Defaults to "IC50".
        max_compounds (int, optional): Maximum number of active compounds to report. Defaults to 5.

    Returns:
        str: Natural language summary of target activities
    """
    params = {
        "target_chembl_id": target_chembl_id,
        "limit": 100,  # Get more to find best compounds
    }
    if activity_type:
        params["standard_type"] = activity_type

    result = chembl_client.get("/activity.json", params=params)

    if "error" in result:
        return f"Error retrieving target activities: {result['error']}"

    activities = result.get("activities", [])
    if not activities:
        filter_text = f" with {activity_type} data" if activity_type else ""
        return f"No compounds found{filter_text} for target {target_chembl_id}"

    # Get target name
    target_result = chembl_client.get(
        "/target.json",
        params={"target_chembl_id": target_chembl_id, "limit": 1},
    )

    target_name = "Unknown target"
    if "error" not in target_result and target_result.get("targets"):
        target_name = target_result["targets"][0].get("pref_name", target_name)

    # Group by compound and find best activity
    compound_activities = {}
    for act in activities:
        if not act.get("standard_value") or not act.get("molecule_chembl_id"):
            continue

        mol_id = act["molecule_chembl_id"]
        mol_name = act.get("molecule_pref_name", mol_id)

        if mol_id not in compound_activities:
            compound_activities[mol_id] = {
                "name": mol_name,
                "best_value": float("inf"),
                "best_type": "",
                "units": "",
            }

        value = float(act["standard_value"])
        if value < compound_activities[mol_id]["best_value"]:
            compound_activities[mol_id]["best_value"] = value
            compound_activities[mol_id]["best_type"] = act.get("standard_type", "")
            compound_activities[mol_id]["units"] = act.get("standard_units", "")

    # Sort by potency and create summary
    sorted_compounds = sorted(
        compound_activities.items(), key=lambda x: x[1]["best_value"]
    )[:max_compounds]

    if not sorted_compounds:
        return f"No valid activity data found for {target_name} ({target_chembl_id})"

    summary_parts = [
        f"Most potent compounds against {target_name} ({target_chembl_id}):"
    ]

    for mol_id, data in sorted_compounds:
        # Format value appropriately
        value = data["best_value"]
        if value < 0.1:
            value_str = f"{value:.2e}"
        elif value < 1000:
            value_str = f"{value:.1f}"
        else:
            value_str = f"{value:.0f}"

        compound_name = data["name"] if data["name"] != mol_id else ""
        name_part = f" ({compound_name})" if compound_name else ""

        summary_parts.append(
            f"• {mol_id}{name_part}: {data['best_type']} = {value_str} {data['units']}"
        )

    total_compounds = len(compound_activities)
    if total_compounds > max_compounds:
        summary_parts.append(
            f"(Showing top {max_compounds} of {total_compounds} compounds with activity data)"
        )

    return "\n".join(summary_parts)


# ============================ Function List ============================

CHEMBL_TOOLS = [
    search_chembl_id,
    get_compound_properties,
    get_compound_bioactivities_summary,
    get_drug_info_summary,
    search_target_id,
    get_target_activities_summary,
]


if __name__ == "__main__":
    import dotenv
    import threading

    dotenv.load_dotenv("../../../.env")

    def test_chembl():
        result = search_chembl_id("aspirin")
        print(f"Thread {threading.current_thread().name}: {result[:100]}...")

    # Test with 10 threads
    threads = []
    for i in range(10):
        t = threading.Thread(target=test_chembl, name=f"Thread-{i}")
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    print("All threads completed")
