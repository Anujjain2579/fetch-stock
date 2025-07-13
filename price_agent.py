import os
from datetime import datetime, timezone
from typing import Optional

import databento as db
from uagents import Model
from dotenv import load_dotenv

load_dotenv()  # pulls DATABENTO_API_KEY from .env
DATABENTO_API_KEY = os.getenv("DATABENTO_API_KEY")
if not DATABENTO_API_KEY:
    raise ValueError("DATABENTO_API_KEY missing – add it to .env")

# ── Schema definitions
class PriceRequest(Model):
    ticker: str
    start: Optional[str] = None   # ISO date (UTC); defaults to today 00:00
    limit: Optional[int] = 5000  # max rows to pull


class PriceResponse(Model):
    results: str                  # human-readable summary


# ── Helper used by both protocols & chat workflow
async def get_price_data(
    ticker: str,
    start: str,
    limit: int = 5000,
) -> str:
    """
    Pull ITCH *mbo* rows from Databento and return a concise summary.
    """
    if start is None:
        start = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    client = db.Historical(DATABENTO_API_KEY)
    print()
    try:
        df = (
            client.timeseries.get_range(
                dataset="XNAS.ITCH",
                schema="mbo",
                symbols=ticker.upper(),
                start="2023-08-17",
                limit=limit,
            )
            .to_df()
        )
    except Exception as exc:
        return f"Error contacting Databento: {exc}"

    if df.empty:
        return f"No data returned for {ticker.upper()} (check symbol or date)."

    latest = df.iloc[-1]
    # ITCH prices are in ten-thousandths of a dollar
    price = latest["price"]
    size = latest["size"]
    ts = latest.name
    return (
        f"Latest {ticker.upper()} trade: ${price:,.2f} "
        f"({size} shares) @ {ts}.  Rows fetched: {len(df):,}"
    )
