"""
Utility functions for robust Google Sheets data handling.
"""

import pandas as pd
from typing import List, Any, Optional
import logging

logger = logging.getLogger(__name__)

def safe_sheet_to_dataframe(sheet_data: List[List[Any]], expected_columns: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Safely convert Google Sheets API data (list of lists) to a pandas DataFrame.
    Handles missing/extra columns and empty rows gracefully.

    Args:
        sheet_data: List of lists as returned by Google Sheets API (first row is header).
        expected_columns: Optional list of expected column names. If provided, ensures DataFrame has these columns (adds missing as NaN, drops extras).

    Returns:
        pd.DataFrame: DataFrame with cleaned columns and rows.
    """
    if not sheet_data or not isinstance(sheet_data, list) or not sheet_data[0]:
        logger.warning("safe_sheet_to_dataframe: Received empty or malformed sheet_data. Returning empty DataFrame.")
        return pd.DataFrame(columns=expected_columns if expected_columns else [])

    header = [str(col).strip() for col in sheet_data[0]]
    rows = sheet_data[1:] if len(sheet_data) > 1 else []
    df = pd.DataFrame(rows, columns=header)

    logger.info(f"safe_sheet_to_dataframe: Created DataFrame with shape {df.shape} and columns: {df.columns.tolist()}")

    # If expected_columns is provided, reindex and fill missing columns with NaN
    if expected_columns:
        missing_cols = [col for col in expected_columns if col not in df.columns]
        extra_cols = [col for col in df.columns if col not in expected_columns]
        if missing_cols:
            logger.warning(f"safe_sheet_to_dataframe: Missing expected columns: {missing_cols}")
        if extra_cols:
            logger.info(f"safe_sheet_to_dataframe: Extra columns present: {extra_cols}")
        df = df.reindex(columns=expected_columns)
    return df
