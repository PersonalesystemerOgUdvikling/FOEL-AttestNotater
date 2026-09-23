"""
THIS IS A TEST SCRIPT
"""

import os
import sys
import json

from OpenOrchestrator.orchestrator_connection.connection import OrchestratorConnection

from mbu_dev_shared_components.getorganized.objects import CaseDataJson

from .case_handler import CaseHandler

from .file_handler import FileHandler

from . import helper_functions

LINE_BREAK = "\n\n\n------------------------------------------------------------------------------------------------------------------\n\n\n"


class DatabaseError(Exception):
    """Custom exception for database related errors."""


class RequestError(Exception):
    """Custom exception for request related errors."""


def identify_employee_folders(
    case_handler: CaseHandler,  # A handler to interact with the case management system
    case_data_handler: CaseDataJson,  # A handler to interact with case data in JSON format - this handler helps create the json data, used in the case_handler
    case_type: str,  # The type of case to be handled (e.g., "PER" for employee cases)
    case_title: str,  # The title of the case to be handled (e.g., "Lønbilag" for salary cases)
    cpr_dicts: str,  # SELV - det CPR-nummer der skal slås op
):
    """
    main func
    """
    cpr, data = next(iter(cpr_dicts.items()))
    tjenestenummer = data.get("tjenestenummer")

    person_full_name, person_go_id = helper_functions.contact_lookup(case_handler=case_handler, ssn=cpr)

    properties_for_case_search = {
        "ows_Title": case_title,
    }

    salary_case_info = helper_functions.check_case_folder(
        case_data_handler=case_data_handler,
        case_handler=case_handler,
        case_type=case_type,
        person_full_name=person_full_name,
        person_go_id=person_go_id,
        ssn=cpr,
        include_name=True,
        returned_cases_number="25",
        field_properties=properties_for_case_search
    )

    # Found 0 case folders - nothing to check, return None
    if not salary_case_info:
        salary_case_id = None

    else:
        # Whether we found 1 or several, we still verify the tjenestenummer matches -
        # a single result is not automatically trusted.
        matching_case_ids = helper_functions.identify_correct_case_by_employment_code(
            case_handler=case_handler,
            salary_case_info=salary_case_info,
            tjenestenummer=tjenestenummer
        )

        if len(matching_case_ids) > 1:
            return "MultipleCasesFound"  # Return a specific string to indicate multiple cases found
            raise LookupError(
                f"Fandt {len(matching_case_ids)} sager for CPR {cpr}, der matcher tjenestenummer {tjenestenummer} "
                f"- forventede præcis 1. Matches: {matching_case_ids}"
            )

        salary_case_id = matching_case_ids[0] if matching_case_ids else None

    print(f"CPR: {cpr} -> Salary case ID: {salary_case_id}")

    return salary_case_id