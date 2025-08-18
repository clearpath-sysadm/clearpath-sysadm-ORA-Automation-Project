Here is the updated action plan to ensure robust, error-free DataFrame handling from Google Sheets data, including validation for downstream safety:

Implement safe_sheet_to_dataframe utility in utils/google_sheets_utils.py to robustly construct DataFrames from Google Sheets data, handling missing/malformed rows and columns.
Implement a validate_dataframe utility in the same module. This function should:
Accept a DataFrame and a list of required columns.
Check for presence of all required columns.
Check for NaN values in critical columns.
Raise a clear exception or log an error if validation fails.
Refactor all code locations (e.g., in src/services/reporting_logic/report_data_loader.py) that construct DataFrames from Google Sheets to:
Use safe_sheet_to_dataframe for construction.
Immediately call validate_dataframe with the required columns for that context.
Update error handling and logging to ensure that any validation failure is visible and actionable (e.g., log error, raise exception, or skip processing as appropriate).
Document the new standard in your codebase (e.g., in README or module docstring): "All DataFrames constructed from Google Sheets must use safe_sheet_to_dataframe and be validated with validate_dataframe before downstream use."
(Optional) Add unit tests for both utilities to ensure they handle edge cases and failures as expected.