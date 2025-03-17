from ib_insync import *
import pandas as pd
from datetime import datetime, timedelta
import time
import os
import math

class OptionsDataCollector:
    def __init__(self):
        self.ib = IB()
        self.tickers = ['VOO', 'TSLA', 'AAPL']
        self.dataframes = {ticker: pd.DataFrame() for ticker in self.tickers}
        self.save_path = 'options_data'
        
        if not os.path.exists(self.save_path):
            os.makedirs(self.save_path)

    def connect_to_ib(self):
        try:
            self.ib.connect('127.0.0.1', 4001, clientId=1)
            self.ib.reqMarketDataType(3)  # 3 = Delayed data
            print("Connected to Interactive Brokers")
        except Exception as e:
            print(f"Connection error: {str(e)}")
            raise

    def get_current_price(self, ticker):
        """Get current price using delayed market data if real-time is unavailable."""
        try:
            contract = Stock(ticker, 'SMART', 'USD')
            qualified_contracts = self.ib.qualifyContracts(contract)
            if not qualified_contracts:
                raise ValueError(f"Could not qualify contract for {ticker}")

            ticker_data = self.ib.reqMktData(qualified_contracts[0], snapshot=True, regulatorySnapshot=False)  # Request delayed data

            # Wait for data to arrive (up to 10 seconds)
            for _ in range(20):  # 20 * 0.5 = 10 seconds
                self.ib.sleep(0.5)
                if ticker_data.last or ticker_data.close:
                    break

            price = ticker_data.last if ticker_data.last else ticker_data.close
            if price and not math.isnan(price):
                return price

            raise ValueError(f"No valid price data for {ticker}")

        except Exception as e:
            print(f"Error getting price for {ticker}: {str(e)}")
            return None


    def get_nearest_expiries(self):
        """Get today's and tomorrow's expiry dates"""
        today = datetime.now()
        tomorrow = today + timedelta(days=1)
        return [today.strftime('%Y%m%d'), tomorrow.strftime('%Y%m%d')]

    def get_atm_strikes(self, ticker):
        """Get at-the-money strike prices with better error handling"""
        current_price = self.get_current_price(ticker)
        
        if current_price is None or math.isnan(current_price):
            print(f"Unable to get valid price for {ticker}")
            return []
            
        try:
            # Get strikes around current price
            base_strike = round(current_price)
            strikes = [
                base_strike - 2,
                base_strike - 1,
                base_strike,
                base_strike + 1,
                base_strike + 2
            ]
            return [strike for strike in strikes if strike > 0]
            
        except Exception as e:
            print(f"Error calculating strikes for {ticker}: {str(e)}")
            return []

    def create_option_contracts(self, ticker):
        """Create option contracts for both calls and puts"""
        contracts = []
        expiries = self.get_nearest_expiries()
        strikes = self.get_atm_strikes(ticker)
        
        if not strikes:
            print(f"No valid strikes found for {ticker}")
            return []

        for expiry in expiries:
            for strike in strikes:
                for right in ['C', 'P']:
                    contract = Option(ticker, expiry, strike, right, 'SMART', 'USD')
                    contracts.append(contract)
        
        return contracts

    def process_market_data(self, ticker, data):
        """Process market data and add to dataframe"""
        try:
            if not data or not data.contract.right in ['C', 'P']:
                return

            current_time = datetime.now()
            
            new_row = {
                'timestamp': current_time,
                'ticker': ticker,
                'expiry': data.contract.lastTradeDateOrContractMonth,
                'strike': data.contract.strike,
                'right': data.contract.right,
                'bid': data.bid if not math.isnan(data.bid) else None,
                'ask': data.ask if not math.isnan(data.ask) else None,
                'last': data.last if not math.isnan(data.last) else None,
                'volume': data.volume if not math.isnan(data.volume) else 0,
                'iv': data.impliedVolatility if not math.isnan(data.impliedVolatility) else None
            }
            
            self.dataframes[ticker] = pd.concat([self.dataframes[ticker], 
                                               pd.DataFrame([new_row])], 
                                              ignore_index=True)
        except Exception as e:
            print(f"Error processing market data for {ticker}: {str(e)}")

    def save_data(self):
        """Save dataframes to CSV files"""
        current_time = datetime.now().strftime('%Y%m%d_%H')
        for ticker in self.tickers:
            if not self.dataframes[ticker].empty:
                filename = f"{self.save_path}/{ticker}_options_{current_time}.csv"
                self.dataframes[ticker].to_csv(filename, index=False)
                print(f"Data saved for {ticker} at {current_time}")

    def run(self):
        """Main run loop"""
        last_save = datetime.now()
        
        try:
            self.connect_to_ib()
            
            while True:
                for ticker in self.tickers:
                    try:
                        print(f"Processing {ticker}...")
                        contracts = self.create_option_contracts(ticker)
                        
                        if not contracts:
                            print(f"No valid contracts created for {ticker}")
                            continue
                            
                        # Request market data for each contract
                        for contract in contracts:
                            try:
                                qualified = self.ib.qualifyContracts(contract)
                                if qualified:
                                    market_data = self.ib.reqMktData(qualified[0],snapshot=False, regulatorySnapshot=False)
                                    self.ib.sleep(1)  # Wait for data to arrive
                                    self.process_market_data(ticker, market_data)
                            except Exception as e:
                                print(f"Error processing contract for {ticker}: {str(e)}")
                                continue
                            
                    except Exception as e:
                        print(f"Error processing {ticker}: {str(e)}")
                        continue

                # Save data every hour
                if (datetime.now() - last_save).seconds >= 3600:
                    self.save_data()
                    last_save = datetime.now()

                # Wait until next minute
                time.sleep(10)

        except KeyboardInterrupt:
            print("\nStopping data collection...")
            self.save_data()
        
        except Exception as e:
            print(f"Critical error: {str(e)}")
            
        finally:
            if self.ib.isConnected():
                self.ib.disconnect()
                print("Disconnected from Interactive Brokers")

if __name__ == "__main__":
    collector = OptionsDataCollector()
    collector.run()