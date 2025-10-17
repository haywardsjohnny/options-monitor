#!/usr/bin/env python3
import os
import sys
import time
import argparse
import logging
import requests
import pandas as pd
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

load_dotenv()
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")

if not POLYGON_API_KEY:
    logging.error("Missing POLYGON_API_KEY in .env file")
    sys.exit(1)

def fetch_options_trades_polygon(underlying, limit=200):
    headers = {"Authorization": f"Bearer {POLYGON_API_KEY}"}

    url = f"https://api.polygon.io/v3/reference/options/contracts?underlying_ticker={underlying}&limit=200"
    try:
        r = requests.get(url, headers=headers)
        r.raise_for_status()
    except Exception as e:
        logging.error(f"Contract lookup failed for {underlying}: {e}")
        return pd.DataFrame()

    contracts = r.json().get("results", [])
    if not contracts:
        logging.warning(f"No contracts found for {underlying}")
        return pd.DataFrame()

    contracts_sorted = sorted(contracts, key=lambda x: x["expiration_date"])
    nearest_exp = contracts_sorted[0]["expiration_date"]

    spot_url = f"https://api.polygon.io/v2/aggs/ticker/{underlying}/prev?apiKey={POLYGON_API_KEY}"
    try:
        r_spot = requests.get(spot_url)
        r_spot.raise_for_status()
        spot = r_spot.json()["results"][0]["c"]
    except Exception as e:
        logging.error(f"Failed to fetch spot for {underlying}: {e}")
        return pd.DataFrame()

    valid_contracts = [
        c for c in contracts_sorted
        if c["expiration_date"] == nearest_exp and abs(c["strike_price"] - spot) / spot <= 0.3
    ]

    selected = [c["ticker"] for c in valid_contracts[:5]]
    logging.info(f"{underlying}: Selected contracts {selected}")

    trades = []
    for contract in selected:
        t_url = f"https://api.polygon.io/v3/trades/{contract}?limit={limit}&apiKey={POLYGON_API_KEY}"
        try:
            r = requests.get(t_url)
            if not r.ok:
                logging.warning(f"{underlying}: No trades for {contract}")
                continue
            results = r.json().get("results", [])
            trades.extend(results)
        except Exception as e:
            logging.error(f"Error fetching trades for {contract}: {e}")

    if trades:
        df = pd.DataFrame(trades)
        logging.info(f"{underlying}: Retrieved {len(df)} trades")
        return df
    else:
        logging.warning(f"{underlying}: No trades collected")
        return pd.DataFrame()

def monitor_once(symbols):
    for s in symbols:
        df = fetch_options_trades_polygon(s, limit=200)
        if not df.empty:
            logging.info(f"{s}: Sample trades\n{df.head(3)}")
        time.sleep(1)

def run_monitor(symbols, interval, daemon=False):
    if daemon:
        scheduler = BackgroundScheduler()
        scheduler.add_job(lambda: monitor_once(symbols), "interval", minutes=interval)
        scheduler.start()
        logging.info(f"Scheduler started: polling every {interval} minutes for symbols: {symbols}")
        try:
            while True:
                time.sleep(10)
        except (KeyboardInterrupt, SystemExit):
            scheduler.shutdown()
    else:
        monitor_once(symbols)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", nargs="+", default=["ORCL", "AAPL", "TSLA", "NBIS"])
    parser.add_argument("--interval", type=int, default=15)
    parser.add_argument("--daemon", action="store_true")
    args = parser.parse_args()

    run_monitor(args.symbols, args.interval, daemon=args.daemon)
