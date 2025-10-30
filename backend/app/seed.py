import random
from datetime import date, timedelta
from typing import List, Tuple
from .settings import Settings
from .db.duckdb_driver import DuckDBDriver
from .db.clickhouse_driver_impl import ClickHouseDriver

REGIONS = ["North", "South", "East", "West"]
CATEGORIES = ["Beverages", "Snacks", "Household", "Personal Care"]
STORES = [(f"S{i:03}", f"Store {i:03}") for i in range(1, 13)]


def generate_dates(months: int = 12) -> List[date]:
    today = date.today().replace(day=1)
    dates: List[date] = []
    for m in range(months):
        month_start = (today.replace(day=1))
        # go back m months
        year = month_start.year
        month = month_start.month - m
        while month <= 0:
            month += 12
            year -= 1
        d = date(year, month, 1)
        # generate 15 random days per month
        for i in range(15):
            day = 1 + random.randint(0, 27)
            day = min(day, 28)
            dates.append(date(d.year, d.month, day))
    dates.sort()
    return dates


def seed_repo(repo_type: str) -> None:
    settings = Settings()
    if repo_type == "clickhouse":
        repo = ClickHouseDriver(settings)
        insert = (
            "INSERT INTO retail_sales (date, store_id, store_name, region, category, sku, units, net_sales) VALUES"
        )
        values = []
        for d in generate_dates():
            for (store_id, store_name) in random.sample(STORES, k=6):
                region = random.choice(REGIONS)
                category = random.choice(CATEGORIES)
                sku = f"SKU-{random.randint(1000, 9999)}"
                units = random.randint(1, 25)
                net_sales = round(units * random.uniform(3.5, 25.0), 2)
                values.append((d, store_id, store_name, region, category, sku, units, net_sales))
        repo.client.execute("TRUNCATE TABLE IF EXISTS retail_sales")
        repo.client.execute(insert, values)
        print(f"Seeded {len(values)} rows into ClickHouse")
    else:
        repo = DuckDBDriver(settings)
        repo.conn.execute("DELETE FROM retail_sales")
        rows = []
        for d in generate_dates():
            for (store_id, store_name) in random.sample(STORES, k=6):
                region = random.choice(REGIONS)
                category = random.choice(CATEGORIES)
                sku = f"SKU-{random.randint(1000, 9999)}"
                units = random.randint(1, 25)
                net_sales = round(units * random.uniform(3.5, 25.0), 2)
                rows.append((d, store_id, store_name, region, category, sku, units, net_sales))
        repo.conn.executemany(
            "INSERT INTO retail_sales VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows
        )
        print(f"Seeded {len(rows)} rows into DuckDB")


if __name__ == "__main__":
    settings = Settings()
    seed_repo(settings.db_driver)

