from ib_insync import *
import time

ib = IB()
ib.connect('127.0.0.1', 7497, clientId=1)

contract = Stock('VOO', 'SMART', 'USD')
ib.qualifyContracts(contract)
[ticker] = ib.reqTickers(contract)
vooValue = ticker.marketPrice()

print(f"value: {vooValue}")

chains = ib.reqSecDefOptParams(contract.symbol, "", contract.secType, contract.conId)
chain = next(c for c in chains if c.tradingClass == "VOO" and c.exchange == "SMART")

print(chain)

# Get all strikes
all_strikes = sorted([strike for strike in chain.strikes])[:]
expirations = sorted(exp for exp in chain.expirations)[:]
rights = ["C", "P"]

print(f"Total strikes: {len(all_strikes)}")
print(f"Total expirations: {len(expirations)}")

# Define batch sizes
strike_batch_size = 5  # Process 5 strikes at a time
batch_delay = 0.5  # Sleep time between batches in seconds

# Initialize contractData list to store all results
all_contract_data = []

# Process in batches of strikes
for i in range(0, len(all_strikes), strike_batch_size):
    batch_strikes = all_strikes[i:i + strike_batch_size]
    print(
        f"Processing strikes batch {i // strike_batch_size + 1}/{(len(all_strikes) - 1) // strike_batch_size + 1}: {batch_strikes}")

    # Create contracts for this batch of strikes
    batch_contracts = [
        Option("VOO", expiration, strike, right, "SMART", tradingClass="VOO")
        for right in rights
        for expiration in expirations
        for strike in batch_strikes
    ]

    try:
        # Qualify and request tickers for this batch
        qualified_contracts = ib.qualifyContracts(*batch_contracts)
        batch_tickers = ib.reqTickers(*qualified_contracts)

        # Extract data from this batch
        for t in batch_tickers:
            # Extract contract properties
            contract_dict = {
                'conId': t.contract.conId,
                'symbol': t.contract.symbol,
                'lastTradeDateOrContractMonth': t.contract.lastTradeDateOrContractMonth,
                'strike': t.contract.strike,
                'right': t.contract.right,
                'multiplier': t.contract.multiplier,
                'exchange': t.contract.exchange,
                'currency': t.contract.currency,
                'localSymbol': t.contract.localSymbol,
                'tradingClass': t.contract.tradingClass
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
                'bboExchange': t.bboExchange if hasattr(t, 'bboExchange') else None,
                'snapshotPermissions': t.snapshotPermissions if hasattr(t, 'snapshotPermissions') else None,
                'undPrice': vooValue  # Adding the underlying price
            }

            # Combine both dictionaries
            entry = {**contract_dict, **ticker_dict}
            all_contract_data.append(entry)

        print(f"Batch completed. Collected {len(batch_tickers)} tickers.")

    except Exception as e:
        print(f"Error processing batch: {e}")

    # Sleep between batches to avoid rate limiting
    if i + strike_batch_size < len(all_strikes):
        print(f"Sleeping for {batch_delay} seconds before next batch...")
        time.sleep(batch_delay)

# Convert all collected data to DataFrame and save
if all_contract_data:
    final = util.df(all_contract_data)
    print(f"Total contracts collected: {len(final)}")
    final.to_csv("all_options_data.csv", index=False, sep=",")
    print("Data saved to all_options_data.csv")
else:
    print("No data collected!")

ib.disconnect()
print("IB connection closed")