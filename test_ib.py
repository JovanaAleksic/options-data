from ib_insync import *

ib = IB()
ib.connect('127.0.0.1', 7497, clientId=1)

contract = Stock('VOO', 'SMART', 'USD')
ib.qualifyContracts(contract)
[ticker]=ib.reqTickers(contract)
vooValue=ticker.marketPrice()

print(f"value: {vooValue}")

chains=ib.reqSecDefOptParams(contract.symbol, "", contract.secType, contract.conId)
chain=next(c for c in chains if c.tradingClass == "VOO" and c.exchange == "SMART")

print(chain)

strikes = [
	strike for strike in chain.strikes
	if strike % 5 == 0
	and vooValue - 20 < strike < vooValue + 20
	]
# strikes = [strike for strike in chain.strikes]


expirations = sorted(exp for exp in chain.expirations)[:]
rights = ["C", "P"]

print(expirations)

contracts=[
	Option("VOO", expiration, strike, right, "SMART", tradingClass="VOO")
	for right in rights
	for expiration in expirations
	for strike in strikes
	]


contracts = ib.qualifyContracts(*contracts)
tickers = ib.reqTickers(*contracts)
print(tickers[0])

# Capture all ticker attributes
contractData = []
for t in tickers:
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
    contractData.append(entry)

# Convert to DataFrame and save
final = util.df(contractData)
final.to_csv("options_test.csv", index=False, sep=",")

ib.disconnect()
