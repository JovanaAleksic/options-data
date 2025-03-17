from ib_insync import *
import time
import pandas as pd

ib = IB()
ib.connect('127.0.0.1', 7497, clientId=1)

contract = Stock('SPY', 'SMART', 'USD')
ib.qualifyContracts(contract)
[ticker] = ib.reqTickers(contract)
spyValue = ticker.marketPrice()

print(f"value: {spyValue}")

chains = ib.reqSecDefOptParams(contract.symbol, "", contract.secType, contract.conId)
chain = next(c for c in chains if c.tradingClass == "SPY" and c.exchange == "SMART")

print(chain)

all_strikes = [strike for strike in chain.strikes
               if strike < spyValue*1.05 and strike > spyValue*0.95]
print(all_strikes)
expirations = sorted(exp for exp in chain.expirations)[:2]
rights = ["C", "P"]

print(f"Total possible strikes: {len(all_strikes)}")
print(f"Total expirations: {len(expirations)}")

# Master list to collect all data across batches
all_contract_data = []


# Create contract definitions for this batch
batch_contract_defs = [
    Option("SPY", expiration, strike, right, "SMART", tradingClass="SPY")
    for right in rights
    for expiration in expirations
    for strike in all_strikes
]


# Try to qualify the contracts - this will filter out invalid combinations
valid_contracts = ib.qualifyContracts(*batch_contract_defs)
print(f"Qualified {len(valid_contracts)} valid contracts out of {len(batch_contract_defs)} possibilities")

# Request tickers only for valid contracts
tickers = ib.reqTickers(*valid_contracts)
print(f"Received {len(tickers)} tickers in batch")

if tickers:
    print(f"Sample ticker: {tickers[0]}")

# Process the valid tickers
for t in tickers:
    # Skip invalid/empty tickers
    if not hasattr(t, 'contract') or not t.contract:
        continue

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

    # Extract ticker properties (same as before)
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


    # Combine both dictionaries
    entry = {**contract_dict, **ticker_dict}
    all_contract_data.append(entry)


# After all batches are processed, write everything to CSV once
if all_contract_data:
    print(f"Collected data for {len(all_contract_data)} contracts")
    final = pd.DataFrame(all_contract_data)
    final.to_csv("options_spy.csv", index=False, sep=",")
    print("Data saved")
else:
    print("No data collected!")

ib.disconnect()
print("IB connection closed")