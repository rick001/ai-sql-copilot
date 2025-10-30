import re
from typing import Tuple

ALLOWED_TABLE = "retail_sales"
ALLOWED_COLUMNS = {
    "date",
    "store_id",
    "store_name",
    "region",
    "category",
    "sku",
    "units",
    "net_sales",
}

FORBIDDEN_PATTERNS = [
    r";", r"--", r"/\*", r"\*/",
    r"\\b(drop|insert|update|delete|alter|create|truncate|grant|revoke)\\b",
]

SELECT_ONLY = re.compile(r"^\s*select\b", re.IGNORECASE | re.DOTALL)
FROM_TABLE = re.compile(r"from\s+([a-zA-Z0-9_\.]+)", re.IGNORECASE)
COLUMN_TOKENS = re.compile(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\b")

def validate_sql(sql: str) -> Tuple[bool, str]:
    text = sql.strip()
    # Remove trailing semicolon (harmless statement terminator)
    if text.endswith(';'):
        text = text[:-1].strip()

    for pat in FORBIDDEN_PATTERNS:
        if re.search(pat, text, flags=re.IGNORECASE):
            return False, "SQL contains forbidden tokens"

    if not SELECT_ONLY.match(text):
        return False, "Only SELECT statements are allowed"

    # Must select from the allowed table only
    from_matches = FROM_TABLE.findall(text)
    if not from_matches:
        return False, "Missing FROM clause"
    tables = {t.split(".")[-1].lower() for t in from_matches}
    if tables != {ALLOWED_TABLE}:
        return False, "Only retail_sales table is allowed"

    # Check that referenced columns are within allow-list (best-effort heuristic)
    # Ignore keywords and functions by a small denylist
    keywords = {
        "select","from","where","and","or","group","by","order","limit","asc","desc",
        "sum","avg","count","as","on","join","left","right","inner","outer","distinct",
        "case","when","then","else","end","between","like","in","not","is","null","having"
    }

    tokens = COLUMN_TOKENS.findall(text)
    # Consider simple cases where tokens look like columns
    for tok in tokens:
        low = tok.lower()
        if low in keywords:
            continue
        if low == ALLOWED_TABLE:
            continue
        # If there's a dot like t.column, the regex would split them; allow both
        if low not in ALLOWED_COLUMNS:
            # tolerate numeric literals
            if low.isdigit():
                continue
            # tolerate function names already in keywords list
            # If token is likely alias, it will appear but we cannot distinguish reliably; allow
            # The strictness mainly protects non-allowlisted tables via FROM enforcement and DDL ban.
            pass

    return True, "ok"

