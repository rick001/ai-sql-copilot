"""
SQL Translator for ClickHouse
Converts standard SQL syntax to ClickHouse-compatible syntax
"""
import re
from typing import Tuple


def translate_to_clickhouse(sql: str) -> str:
    """
    Translate standard SQL to ClickHouse-compatible syntax.
    
    Handles:
    - CURRENT_DATE -> today()
    - DATE functions
    - INTERVAL syntax (ClickHouse supports it natively but we ensure compatibility)
    - Other common SQL dialect differences
    """
    if not sql:
        return sql
    
    result = sql.strip()
    
    # 1. Date functions
    # CURRENT_DATE -> today()
    result = re.sub(r'\bCURRENT_DATE\b', 'today()', result, flags=re.IGNORECASE)
    result = re.sub(r'\bCURRENT_DATE\s*\(\)', 'today()', result, flags=re.IGNORECASE)
    
    # NOW() -> now() (ClickHouse uses lowercase)
    result = re.sub(r'\bNOW\s*\(\)', 'now()', result, flags=re.IGNORECASE)
    
    # 2. Date arithmetic - ClickHouse supports INTERVAL but fix incorrect patterns
    # Fix toIntervalMonth(N) -> INTERVAL N MONTH (ClickHouse native syntax)
    result = re.sub(r'toIntervalMonth\s*\((\d+)\)', r'INTERVAL \1 MONTH', result, flags=re.IGNORECASE)
    result = re.sub(r'toIntervalDay\s*\((\d+)\)', r'INTERVAL \1 DAY', result, flags=re.IGNORECASE)
    result = re.sub(r'toIntervalYear\s*\((\d+)\)', r'INTERVAL \1 YEAR', result, flags=re.IGNORECASE)
    
    # Fix common patterns like: date - INTERVAL N MONTH
    # ClickHouse syntax: date - INTERVAL N MONTH (already correct)
    # But ensure consistency
    
    # 3. String functions - ClickHouse uses different names
    # LENGTH() -> length() (ClickHouse uses lowercase)
    result = re.sub(r'\bLENGTH\s*\(', 'length(', result, flags=re.IGNORECASE)
    
    # UPPER() -> upper(), LOWER() -> lower()
    result = re.sub(r'\bUPPER\s*\(', 'upper(', result, flags=re.IGNORECASE)
    result = re.sub(r'\bLOWER\s*\(', 'lower(', result, flags=re.IGNORECASE)
    
    # 4. Aggregate functions - ClickHouse supports standard names but ensure lowercase
    # COUNT, SUM, AVG, MAX, MIN are all supported, but be consistent
    # No translation needed for these
    
    # 5. Date extraction - ClickHouse uses toYear(), toMonth(), etc.
    # EXTRACT(YEAR FROM date) -> toYear(date)
    result = re.sub(
        r'EXTRACT\s*\(\s*YEAR\s+FROM\s+([^)]+)\s*\)',
        r'toYear(\1)',
        result,
        flags=re.IGNORECASE
    )
    result = re.sub(
        r'EXTRACT\s*\(\s*MONTH\s+FROM\s+([^)]+)\s*\)',
        r'toMonth(\1)',
        result,
        flags=re.IGNORECASE
    )
    result = re.sub(
        r'EXTRACT\s*\(\s*DAY\s+FROM\s+([^)]+)\s*\)',
        r'toDayOfMonth(\1)',
        result,
        flags=re.IGNORECASE
    )
    
    # YEAR(date) -> toYear(date)
    result = re.sub(r'\bYEAR\s*\(([^)]+)\)', r'toYear(\1)', result, flags=re.IGNORECASE)
    result = re.sub(r'\bMONTH\s*\(([^)]+)\)', r'toMonth(\1)', result, flags=re.IGNORECASE)
    result = re.sub(r'\bDAY\s*\(([^)]+)\)', r'toDayOfMonth(\1)', result, flags=re.IGNORECASE)
    
    # 6. Date formatting - DATE_FORMAT -> formatDateTime (ClickHouse)
    # DATE_FORMAT(date, '%Y-%m') -> formatDateTime(date, '%Y-%m')
    result = re.sub(
        r'DATE_FORMAT\s*\(',
        'formatDateTime(',
        result,
        flags=re.IGNORECASE
    )
    
    # 7. Case sensitivity fixes for ClickHouse functions
    # Ensure proper case for ClickHouse functions that are case-sensitive
    # (Most ClickHouse functions are case-insensitive, but being explicit helps)
    
    # 8. Remove or handle SQL features ClickHouse doesn't support well
    # ROLLUP, CUBE - ClickHouse has GROUPING SETS but different syntax
    # For now, we'll leave them and let ClickHouse error if not supported
    
    return result


def validate_clickhouse_compatibility(sql: str) -> Tuple[bool, str]:
    """
    Check if SQL uses functions that ClickHouse doesn't support.
    Returns (is_compatible, error_message)
    """
    sql_upper = sql.upper()
    
    # Check for unsupported patterns
    unsupported_patterns = [
        (r'\bCURRENT_TIMESTAMP\b', 'CURRENT_TIMESTAMP - use now() instead'),
        (r'\bCURRENT_TIME\b', 'CURRENT_TIME - use now() instead'),
        # Add more as needed
    ]
    
    for pattern, error_msg in unsupported_patterns:
        if re.search(pattern, sql, flags=re.IGNORECASE):
            return False, f"Unsupported function: {error_msg}"
    
    return True, "ok"

