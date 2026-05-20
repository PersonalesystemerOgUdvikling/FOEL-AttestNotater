import os
import csv

import pandas as pd


class FileHandler:
    """
    A class to read data from Excel files with .xlsx format located in a specified directory.

    Attributes:
    -----------
    directory : str
        The directory where Excel files are stored.

    Methods:
    --------
    get_cpr_values(sheet_name: str, filename: str) -> List[str]:
        Reads the 'CPR' column from the given sheet in the specified file,
        ensuring values are stored as strings with preserved leading zeros, and returns them sorted.
    """
    def __init__(self, directory: str):
        """
        Initializes the ExcelHandler with the directory containing Excel files.

        Parameters:
        -----------
        directory : str
            The directory path where Excel files are stored.
        """
        if not os.path.isdir(directory):
            raise ValueError(f"{directory} is not a valid directory.")
        self.directory = directory

    def _get_file_path(self, filename: str) -> str:
        """
        Helper method to construct the full file path from the directory and filename.

        Parameters:
        -----------
        filename : str
            The name of the Excel file.

        Returns:
        --------
        str
            The full path to the Excel file.
        """
        return os.path.join(self.directory, filename)

    def build_cpr_mapping(self, filename: str, sheet_name: str) -> dict:
        """
        Reads each row in an Excel file (identified by 'filename' and 'sheet_name') and
        returns a dictionary of the form:

            {
                "some_cpr": {
                    "tjenestenummer": ...,
                    "navn": ...,
                    "stilling": ...
                },
                "another_cpr": {
                    "tjenestenummer": ...,
                    "navn": ...,
                    "stilling": ...
                },
                ...
            }

        It assumes the Excel has columns:
            - "Tjenestenummer"
            - "CPR"
            - "Navn"
            - "Stilling"

        and that "CPR" is used as the key in the returned dictionary.

        The DataFrame is first sorted by the numeric value of the "CPR" column (smallest first).
        """

        file_path = self._get_file_path(filename)

        # Read the Excel file with converters to ensure values are read as strings
        df = pd.read_excel(
            file_path,
            sheet_name=sheet_name,
            converters={
                'CPR': str,
                'Tjenestenummer': str,
                'Navn': str,
                'Stilling': str
            }
        )

        # Ensure required columns exist
        required_cols = ['CPR', 'Tjenestenummer', 'Navn', 'Stilling']
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Missing required column '{col}' in the sheet.")

        # Sort the DataFrame, in ascending order, by the numeric value of the CPR column - this assumes that CPR values are numeric even if stored as strings.
        df.sort_values(by='CPR', key=lambda col: col.astype(int), inplace=True)

        # Build the dictionary, preserving the sorted order.
        cpr_dict = {}
        for _, row in df.iterrows():
            cpr_value = row['CPR']

            # Skip rows with missing CPR value
            if pd.isna(cpr_value):
                continue

            # Remove any accidental whitespace
            cpr_value = cpr_value.strip()

            cpr_dict[cpr_value] = {
                "tjenestenummer": row['Tjenestenummer'] if not pd.isna(row['Tjenestenummer']) else "",
                "navn": row['Navn'] if not pd.isna(row['Navn']) else "",
                "stilling": row['Stilling'] if not pd.isna(row['Stilling']) else ""
            }

        return cpr_dict
