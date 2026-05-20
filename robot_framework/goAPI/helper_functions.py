"""
This module provides helper functions.
"""

import xml.etree.ElementTree as ET

from typing import Optional, Tuple

from mbu_dev_shared_components.getorganized.objects import CaseDataJson

from .case_handler import CaseHandler


class DatabaseError(Exception):
    """Custom exception for database related errors."""


class RequestError(Exception):
    """Custom exception for request related errors."""

def mask_cpr(cpr):
    if not cpr:
        return "<missing>"
    cpr = str(cpr)
    return "***" + cpr[-4:]


def contact_lookup(case_handler: CaseHandler, ssn: str) -> Optional[Tuple[str, str]]:
    """
    Perform contact lookup.
    Using the provided SSN, this function retrieves the person's full name and ID from the case handler.

    Returns:
        A tuple containing the person's full name and ID if successful, otherwise None.
    """

    response = case_handler.contact_lookup(ssn, '/personalemapper/_goapi/contacts/readitem')

    if not response.ok:
        raise RequestError(
            f"GO API contact lookup failed. "
            f"Status code: {response.status_code}. "
            f"Response body: {response.text[:1000]}. "
            f"Case handler: {case_handler}. "
            f"CPR: {mask_cpr(ssn)}."
    )

    person_data = response.json()

    person_full_name = person_data["FullName"]
    person_go_id = person_data["ID"]

    return person_full_name, person_go_id


def check_case_folder(
    case_data_handler: CaseDataJson,
    case_handler: CaseHandler,
    case_type: str,
    person_full_name: str,
    person_go_id: str,
    ssn: str,
    include_name: bool = True,
    returned_cases_number: str = "25",
    field_properties: dict = None
):
    """
    Check if a case folder exists for the person and update the database. 

    Parameters:
    case_data_handler (CaseDataJson): A handler to interact with the case data in JSON format - this handler helps create the json data, used in the case_handler
    case_handler (CaseHandler): A handler to interact with the case management system
    case_type (str): The type of the case. PER for employee cases, etc.
    person_full_name (str): The full name of the person associated with the case.
    person_id (str): The ID of the person associated with the case.
    person_ssn (str): The Social Security Number of the person associated with the case.
    include_name (str): Whether or not, the person_full_name should be included in the contact_data for the search
    returned_cases_number (str): The number of returned results
    field_properties (dict): A list of desired field properties to add, in order to specify the search

    Returns:
        The case folder ID if it exists, otherwise None.
    """

    # Using the provided parameters, this function creates a JSON string representing a search string, used to retrieve a GetOrganized case folder.
    # The function is dynamic, in the sense that we don't need to spceify the field properties in advance, but can add them dynamically.
    search_data = case_data_handler.generic_search_case_data_json(
        case_type_prefix=case_type,
        person_full_name=person_full_name,
        person_id=person_go_id,
        person_ssn=ssn,
        include_name=include_name,
        returned_cases_number=returned_cases_number,
        field_properties=field_properties
    )

    # After the search data is created in JSON format, we can use the case_handler to search for the case folder, appending the final endpoint for the search
    response = case_handler.search_for_case_folder(case_folder_search_data=search_data, endpoint_path='/_goapi/cases/findbycaseproperties/')

    if not response.ok:
        raise RequestError("Request response failed.")

    # We then parse the response, which is a JSON object, and extract the 'CasesInfo' key, which contains information about the cases found
    # The 'CasesInfo' key contains a list of dictionaries, where each dictionary contains information about a case - typically only 1 case is returned, but we can have multiple cases, if the search was expanded
    cases_info = response.json().get('CasesInfo', [])

    return cases_info


def identify_correct_case_by_employment_code(case_handler: CaseHandler, salary_case_info: list, tjenestenummer: str):
    """
    functiuon doc string
    """

    # We start by iterating through the salary_case_info, which is a list of dictionaries, where each dictionary contains information about a case
    for case in salary_case_info:
        case_id = case.get("CaseID")

        # We split the case_id, so we only get the case_id for the employee folder, where we can check the employment code
        employee_case_id = case_id.rsplit("-", 1)[0]

        # We then use the case_handler to get the metadata for the case, using the case_id
        response = case_handler.get_case_metadata(endpoint_path=f'/_goapi/Cases/Metadata/{employee_case_id}')

        # We parse the metadata string returned from the API, using the parse_metadata function
        formatted_res = parse_metadata(metadata_str=response.json().get("Metadata"))

        # One of the metadata keys is "ows_EmploymentCode", which contains the employment code, related to the case - we check if this key matches the tjenestenummer we are looking for
        if tjenestenummer in formatted_res.get("ows_EmploymentCode"):
            correct_salary_case_id = case_id

            break

    return correct_salary_case_id


def get_salary_case_id_through_metadata(case_handler: CaseHandler, employee_folder_id: str, case_title: str):
    """
    Check if a case folder exists for the person and update the database.

    Returns:
        The case folder ID if it exists, otherwise None.
    """

    # We start by creating an empty string for the case_id, which will be used to store the case id for the salary case
    case_id = ""

    # We then loop from 1 to 15, which is the maximum number of cases we want to check for the employee folder - there should be a maximum of 10 cases for each employee folder, we use 15 to be safe
    for case_number in range(1, 15):
        # We check if the case_number is greater than or equal to 10, and if so, we create the case_id with a leading zero
        if case_number >= 10:
            case_id = f"{employee_folder_id}-0{case_number}"

        # If the case_number is less than 10, we create the case_id with 2 leading zeros
        else:
            case_id = f"{employee_folder_id}-00{case_number}"

        # For each looped case, we use the case_handler to get the metadata for the case, using the case_id
        response = case_handler.get_case_metadata(endpoint_path=f'/_goapi/Cases/Metadata/{case_id}')

        # We parse the metadata string returned from the API, using the parse_metadata function
        formatted_res = parse_metadata(metadata_str=response.json().get("Metadata"))

        # One of the metadata keys is "ows_Title", which refers to the case_title, related to the case - we check if this key matches the case_title we are looking for
        if case_title in formatted_res.get("ows_Title"):
            salary_case_id = case_id

            break

    if not response.ok:
        raise RequestError("Request response failed.")

    if salary_case_id:
        return salary_case_id

    else:
        raise Exception(f"BIG ERROR - DID NOT WORK!!! printing employee_folder_id:\n{employee_folder_id}")


def parse_metadata(metadata_str: str) -> dict:
    """
    Parses an XML metadata string (like the one returned from the API)
    and returns a dictionary of its attributes.

    Parameters:
        metadata_str (str): The metadata string to parse.

    Returns:
        dict: A dictionary with keys and values corresponding to the XML attributes.
    """

    try:
        # Parse the string into an XML element.
        root = ET.fromstring(metadata_str)

        # The attributes of this element are in root.attrib
        return root.attrib

    except ET.ParseError as e:
        print("Error parsing metadata:", e)

        return {}
