# IBKR SPY Options Data Collector

This repository contains code for collecting hourly SPY options data from Interactive Brokers (IBKR) during market hours on trading days.

## Overview

The project automatically collects SPY options data through the Interactive Brokers API using the `ib_insync` library. It focuses on options within 5% of the current SPY price and the next two expiration dates, gathering complete pricing information including Greeks.

## Data Collection Process

The data collection script (`options_creation.py`) connects to IBKR, fetches options data, and saves it to CSV files with the following features:

- Runs hourly during US market hours (9:30 AM - 4:00 PM Eastern Time)
- Only collects on weekdays that aren't US market holidays
- Maintains both historical and latest snapshots of data
- Includes all Greeks (delta, gamma, theta, vega) from multiple price sources

### Technical Details

- Collects options with strikes within +/- 5% of current SPY price
- Captures short term options: 0DTE and 1DTE
- Includes both calls and puts
- Tracks full option contract details and pricing metrics

## Dataset

The collected data is stored in two CSV files:

1. `options_spy_historical.csv`: Contains all historical data points with timestamps
2. `options_spy_latest.csv`: Contains only the most recent data collection
3. 
### Data Collection Status

🔴 **Active Collection in Progress**

The dataset is currently being actively collected and will be updated regularly. 

### Data Fields

The dataset includes numerous fields for each option contract:

- **Contract Information**: Symbol, strike price, expiration date, right (call/put), etc.
- **Pricing Data**: Bid, ask, last price, sizes, volume
- **Greeks**: Delta, gamma, theta, vega for bid, ask, last, and model prices
- **Timestamps**: When each data point was collected

## Requirements

- Python 3.6+
- ib_insync
- pandas
- schedule
- pytz
- Interactive Brokers Trader Workstation (TWS) or IB Gateway running with API connections enabled

## Installation

```bash
pip install ib_insync pandas schedule pytz
```

## Usage

1. Ensure IBKR Trader Workstation or IB Gateway is running and accepting API connections on port 7497
2. Run the data collection script:

```bash
python options_creation.py
```

The script will automatically:
- Check if it's a trading day
- Schedule collections for market hours
- Save data hourly
- Sleep efficiently between collections

## Scheduler Logic

The scheduler is designed to be resource-efficient:

- Performs an initial check at 7:00 AM ET to determine if it's a trading day
- If it's a trading day, schedules all collection points for the day (9:30 AM, 10:00 AM, ...)
- Sleeps efficiently between collections rather than constantly checking
- Reschedules automatically for the next trading day

## Notes

- The script connects to IBKR API at localhost (127.0.0.1) on port 7497 with clientId=1
- Modify the connection parameters if needed for your setup
- The script handles connection errors and will log issues without crashing
- Data is appended to the historical file to prevent loss if the script restarts