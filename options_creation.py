from ib_insync import *
import time
import pandas as pd
import datetime
import schedule
import os
import pytz


def is_market_open():
    """Check if the US market is currently open"""
    # Get current time in Eastern time (US market time)
    eastern = pytz.timezone('US/Eastern')
    now = datetime.datetime.now(eastern)

    # Check if it's a weekday (0 = Monday, 4 = Friday)
    if now.weekday() > 4:  # Weekend
        return False

    # Check if it's within market hours (9:30 AM to 4:00 PM Eastern)
    market_open = now.replace(hour=9, minute=30, second=0)
    market_close = now.replace(hour=16, minute=0, second=0)

    return market_open <= now <= market_close


def get_holidays(year):
    """Get a list of US market holidays for a given year"""
    holidays = [
        # New Year's Day
        datetime.datetime(year, 1, 1),
        # Martin Luther King Jr. Day (third Monday in January)
        datetime.datetime(year, 1, 15) + datetime.timedelta(
            days=(0 - datetime.datetime(year, 1, 15).weekday() + 7) % 7),
        # Presidents' Day (third Monday in February)
        datetime.datetime(year, 2, 15) + datetime.timedelta(
            days=(0 - datetime.datetime(year, 2, 15).weekday() + 7) % 7),
        # Good Friday
        datetime.datetime(year, 4, 18),
        # Memorial Day (last Monday in May)
        datetime.datetime(year, 5, 31) - datetime.timedelta(days=datetime.datetime(year, 5, 31).weekday()),
        # Juneteenth
        datetime.datetime(year, 6, 19),
        # Independence Day
        datetime.datetime(year, 7, 4),
        # Labor Day (first Monday in September)
        datetime.datetime(year, 9, 1) + datetime.timedelta(days=(0 - datetime.datetime(year, 9, 1).weekday() + 7) % 7),
        # Thanksgiving (fourth Thursday in November)
        datetime.datetime(year, 11, 1) + datetime.timedelta(
            days=(3 - datetime.datetime(year, 11, 1).weekday() + 7) % 7 + 21),
        # Christmas
        datetime.datetime(year, 12, 25)
    ]

    # Adjust for weekends
    adjusted_holidays = []
    for holiday in holidays:
        if holiday.weekday() == 5:  # Saturday
            adjusted_holidays.append(holiday - datetime.timedelta(days=1))
        elif holiday.weekday() == 6:  # Sunday
            adjusted_holidays.append(holiday + datetime.timedelta(days=1))
        else:
            adjusted_holidays.append(holiday)

    return adjusted_holidays


def is_holiday():
    """Check if today is a US market holiday"""
    eastern = pytz.timezone('US/Eastern')
    today = datetime.datetime.now(eastern).date()
    holidays = get_holidays(today.year)
    return today in [holiday.date() for holiday in holidays]


def collect_spy_options():
    """Collect SPY options data and update the CSV file"""
    print(f"Starting SPY options data collection...")
    try:
        # Connect to IB
        ib = IB()
        ib.connect('127.0.0.1', 7497, clientId=1)

        contract = Stock('SPY', 'SMART', 'USD')
        ib.qualifyContracts(contract)
        [ticker] = ib.reqTickers(contract)
        spyValue = ticker.marketPrice()

        print(f"SPY value: {spyValue}")

        chains = ib.reqSecDefOptParams(contract.symbol, "", contract.secType, contract.conId)
        chain = next(c for c in chains if c.tradingClass == "SPY" and c.exchange == "SMART")

        # Get strikes within +/- 30% of current price 
        all_strikes = [strike for strike in chain.strikes if strike < spyValue * 1.30 and strike > spyValue * 0.70]
        
        expirations = sorted(exp for exp in chain.expirations)[:]  
        sheaps = expirations[:2] # short term - 0DTE and 1DTE
        leaps = expirations[-2:] # longest term expiration dates
        expirations = sheaps + leaps

        rights = ["C", "P"]

        print(f"Total possible strikes: {len(all_strikes)}")
        print(f"Total expirations: {len(expirations)}")

        # Master list to collect all data
        all_contract_data = []

        # Create contract definitions
        contract_defs = [
            Option("SPY", expiration, strike, right, "SMART", tradingClass="SPY")
            for right in rights
            for expiration in expirations
            for strike in all_strikes
        ]

        # Qualify the contracts
        valid_contracts = ib.qualifyContracts(*contract_defs)
        print(f"Qualified {len(valid_contracts)} valid contracts out of {len(contract_defs)} possibilities")

        # Request tickers for valid contracts
        tickers = ib.reqTickers(*valid_contracts)
        print(f"Received {len(tickers)} tickers")

        # Process the valid tickers
        for t in tickers:
            if not hasattr(t, 'contract') or not t.contract:
                continue

            # Extract contract properties
            contract_dict = {
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'conId': t.contract.conId,
                'symbol': t.contract.symbol,
                'lastTradeDateOrContractMonth': t.contract.lastTradeDateOrContractMonth,
                'strike': t.contract.strike,
                'right': t.contract.right,
                'multiplier': t.contract.multiplier,
                # 'exchange': t.contract.exchange,
                'currency': t.contract.currency,
                # 'localSymbol': t.contract.localSymbol,
                # 'tradingClass': t.contract.tradingClass
            }

            # Extract ticker properties
            ticker_dict = {
                'time': t.time,
                'minTick': t.minTick,
                'bid': t.bid,
                'bidSize': t.bidSize,
                'ask': t.ask,
                'askSize': t.askSize,
                'last': t.last if hasattr(t, 'last') else None,
                'lastSize': t.lastSize if hasattr(t, 'lastSize') else None,
                'high': t.high if hasattr(t, 'high') else None,
                'low': t.low if hasattr(t, 'low') else None,
                'volume': t.volume if hasattr(t, 'volume') else None,
                'close': t.close,
                # 'bboExchange': t.bboExchange if hasattr(t, 'bboExchange') else None,
                # 'snapshotPermissions': t.snapshotPermissions if hasattr(t, 'snapshotPermissions') else None,
                'undPrice': spyValue,  # Adding the underlying price
            }

            # Add bid Greeks if available
            if hasattr(t, 'bidGreeks') and t.bidGreeks:
                ticker_dict.update({
                    'bid_impliedVol': t.bidGreeks.impliedVol,
                    'bid_delta': t.bidGreeks.delta,
                    'bid_optPrice': t.bidGreeks.optPrice,
                    'bid_pvDividend': t.bidGreeks.pvDividend,
                    'bid_gamma': t.bidGreeks.gamma,
                    'bid_vega': t.bidGreeks.vega,
                    'bid_theta': t.bidGreeks.theta,
                    'bid_undPrice': t.bidGreeks.undPrice
                })

            # Add ask Greeks if available
            if hasattr(t, 'askGreeks') and t.askGreeks:
                ticker_dict.update({
                    'ask_impliedVol': t.askGreeks.impliedVol,
                    'ask_delta': t.askGreeks.delta,
                    'ask_optPrice': t.askGreeks.optPrice,
                    'ask_pvDividend': t.askGreeks.pvDividend,
                    'ask_gamma': t.askGreeks.gamma,
                    'ask_vega': t.askGreeks.vega,
                    'ask_theta': t.askGreeks.theta,
                    'ask_undPrice': t.askGreeks.undPrice
                })

            # Add last Greeks if available
            if hasattr(t, 'lastGreeks') and t.lastGreeks:
                ticker_dict.update({
                    'last_impliedVol': t.lastGreeks.impliedVol,
                    'last_delta': t.lastGreeks.delta,
                    'last_optPrice': t.lastGreeks.optPrice,
                    'last_pvDividend': t.lastGreeks.pvDividend,
                    'last_gamma': t.lastGreeks.gamma,
                    'last_vega': t.lastGreeks.vega,
                    'last_theta': t.lastGreeks.theta,
                    'last_undPrice': t.lastGreeks.undPrice
                })

            # Add model Greeks if available
            if hasattr(t, 'modelGreeks') and t.modelGreeks:
                ticker_dict.update({
                    'model_impliedVol': t.modelGreeks.impliedVol,
                    'model_delta': t.modelGreeks.delta,
                    'model_optPrice': t.modelGreeks.optPrice,
                    'model_pvDividend': t.modelGreeks.pvDividend,
                    'model_gamma': t.modelGreeks.gamma,
                    'model_vega': t.modelGreeks.vega,
                    'model_theta': t.modelGreeks.theta,
                    'model_undPrice': t.modelGreeks.undPrice
                })

            # Combine dictionaries
            entry = {**contract_dict, **ticker_dict}
            all_contract_data.append(entry)

        # Disconnect from IB
        ib.disconnect()
        print("IB connection closed")

        # Now create or append to the CSV file
        if all_contract_data:
            current_data = pd.DataFrame(all_contract_data)
            file_path = "options_spy_historical5.csv"

            # Check if file exists to determine whether to append or create new
            if os.path.exists(file_path):
                # Load existing data to append to
                current_data.to_csv(file_path, mode='a', header=False, index=False)
                print(f"Appended {len(current_data)} records to {file_path}")
            else:
                # Create new file
                current_data.to_csv(file_path, index=False)
                print(f"Created new file {file_path} with {len(current_data)} records")

            # Also save latest snapshot for quick access
            current_data.to_csv("options_spy_latest.csv", index=False)
            print(f"Updated latest snapshot with {len(current_data)} records")
        else:
            print("No data collected!")

    except Exception as e:
        print(f"Error collecting options data: {e}")


def run_scheduler():
    def scheduled_task():
        if is_market_open() and not is_holiday():
            collect_spy_options()
        else:
            print(f"{datetime.datetime.now(pytz.timezone('US/Eastern'))}: Market is closed. Skipping data collection.")

    # Schedule the task every 1 minute
    schedule.every(3).minutes.do(scheduled_task)

    print("Scheduler started. Will collect SPY options data every 3 minutes during market hours.")

    # Run once immediately
    scheduled_task()

    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    run_scheduler()