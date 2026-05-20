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
    cpr_dicts: str, # SELV - det CPR-nummer der skal slås op
):
    """
    main func
    """

    # Iterate through each CPR number and its associated data in the dictionary
    for i, (cpr, data) in enumerate(cpr_dicts.items()):
        # Initialize the salary_case_id variable to None for each iteration, so we can freely manipulate it later
        salary_case_id = None

        # Retrieve the employee's name and ID from the case handler using the CPR number
        person_full_name, person_go_id = helper_functions.contact_lookup(case_handler=case_handler, ssn=cpr)
        print(f"iterative_number: {i + 1}\nname: {person_full_name}\nperson_go_id: {person_go_id}\ncpr: {cpr}\n")

        # This dictionary contains the properties we want to use, when searching for the case folder
        properties_for_case_search = {
            "ows_Title": case_title,
        }

        # Attempt 1: Check case folder with initial parameters
        # In the 1st attempt, we include the name in the search, as we want to find the case folder for this specific person, and we also include the case_title as a field property to narrow down the search
        print("Attempt 1")
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
        # In some cases, the search might return more than one case folder, if the person has multiple employment codes
        if len(salary_case_info) > 1:
            print("THIS PERSON HAS MORE THAN 1 CASE FOLDER - IMPORTANT!")

            tjenestenummer = data.get("tjenestenummer")

            # If that is the case, we need to identify the correct case folder by using the employment code (tjenestenummer) from the Excel file
            salary_case_id = helper_functions.identify_correct_case_by_employment_code(case_handler=case_handler, salary_case_info=salary_case_info, tjenestenummer=tjenestenummer)

        else:
            # If the search returns only one case folder, we can simply extract the CaseID from the first item in the list
            if salary_case_info:
                salary_case_id = salary_case_info[0].get('CaseID')

            # In some cases, the search might return no case folder at all - therefore we expand the search by removing the name from the search, whils keeping the ssn, the go_id, and with with the case_title as a field property
            else:
                print("\nAttempt 2")

                salary_case_info_without_name = helper_functions.check_case_folder(case_data_handler=case_data_handler, case_handler=case_handler, case_type=case_type, person_full_name=person_full_name, person_go_id=person_go_id, ssn=cpr, include_name=False, returned_cases_number="25", field_properties=properties_for_case_search)

                if salary_case_info_without_name:
                    salary_case_id = salary_case_info_without_name[0].get('CaseID')

                # Worst case scenario, the search returns no case folder at all - therefore we expand the search by removing the case_title from the search, and only keeping the name, go_id and ssn in the search
                # This will now return all active employee cases for the person, regardless of the case_title
                else:
                    print("\nAttempt 3")

                    all_cases_info = helper_functions.check_case_folder(case_data_handler=case_data_handler, case_handler=case_handler, case_type=case_type, person_full_name=person_full_name, person_go_id=person_go_id, ssn=cpr, include_name=True, returned_cases_number="25", field_properties=None)

                    if all_cases_info:
                        # We fetch the case id of the first case folder in the list, which should be the employee folder
                        employee_folder_id = all_cases_info[0].get('CaseID')

                        # We then use this employee folder id to get the salary case id, by looping the remaining cases in the list, and checking the metadata for each case, until we find the case with a matching case title
                        salary_case_id = helper_functions.get_salary_case_id_through_metadata(case_handler=case_handler, employee_folder_id=employee_folder_id, case_title=case_title)

                    else:
                        salary_case_id = None

        if salary_case_id:
            mapping_entry = {cpr: salary_case_id}

        else:
            mapping_entry = {cpr: "CPR NOT PROPERLY HANDLED - Please investigate this SSN"}

        print(f"\nFinal Salary CPR to Case ID mapping: {mapping_entry}\n")

    return salary_case_id