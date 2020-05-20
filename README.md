# IbPy Native - Interactive Brokers Native Python API

## Installation
Install from PyPI
```sh
pip install ibpy-native
```

Alternatively, install from source. Execute `setup.py` from the root directory.
```sh
python setup.py install
```

__*Always use the newest version while the project is still in alpha!*__

## Usage
```python
import ibpy_native
import pytz

# Set the timezone to match the timezone specified in TWS or IB Gateway when login
# Default timezone - 'America/New_York'
ibpy_native.IBBridge.set_timezone(pytz.timezone('America/New_York'))


# Connect to a running TWS or IB Gateway instance
bridge = ibpy_native.IBBridge(host='127.0.0.1', port=4001, client_id=1, auto_conn=True)
```

An optional parameter `timeout` is available for all APIs implemented in 
`IBBridge`. The timeout value is treated as `X` seconds, and the default timeout 
time has been set to 10 seconds.

```python
# Search the US stock contract of Apple Inc.
aapl = bridge.get_us_stock_contract(symbol='AAPL')

# Ask for the earliest available data point of AAPL
head_time = bridge.get_earliest_data_point(contract=aapl, data_type='TRADES')

# Get all historical ticks of AAPL
#
# It's better to set the timeout value a bit long (e.g. 30~100s) as this API 
# loops to request around 1000 historical ticks for each IB API request due to 
# IB's limitation. IB will slow down the response time after the first 10~20 
# requests, thus the default 10s timeout is likely to be insufficient to wait 
# for the following API responses from IB.
ticks = bridge.get_historical_ticks(contract=aapl, data_type='TRADES', timeout=100)
```

## System requirements
- Python >= 3.5; Pervious versions are not supported (development is based on 
Python 3.7.7)
- _Included IB API version - `9.79.01`_

## Known issues
- Function `IBBridge.get_historical_ticks` may raise an error with error code 
`200` - `No security definition has been found for the request` if the 
connection between IB and the TWS/IB Gateway instance has been dropped 
unexpectedly while requesting the data. It doesn't matter if the connection is 
restored shortly after the disconnection.

## Development status (a.k.a. Words from developers)
Although the project is under the stage of active development, up until now
(ver. 0.1.1) it focuses on retrieving historical ticks for stock & future
contracts from IB. Other security types (e.g. options) may work but those are
not yet tested.

Other features like retrieving account details, place & modify orders are
planned to be implemented in the future, but there is no estimated timeline for 
those atm, as the project is being developed alongside Devtography internal 
algo-trading program. For now, the features will be developed and released when 
needed.

## Contributions
Contributions via pull requests are welcome and encouraged. If there's any 
feature you think is missing, please don't hesitate to implement yourself and 
make a pull request :)

## License
Modules included in `ibpy_native`, except `ibapi` is licensed under the 
[Apache License, Version 2.0](LICENSE.md).

The `ibapi` is 100% developed & owned by Interactive Brokers LLC ("IB"). By 
using this package (`ibpy-native`), you are assumed that you agreed the 
[TWS API Non-Commercial License].

## Remarks
`ibpy_native` is not a product of Interactive Brokers, nor is this project 
affiliated with IB. If you'd like to use `ibpy_native` in any commercial 
application/product, you must contact Interactive Brokers LLC for permission 
of using IB API commercially.

[TWS API Non-Commercial License]: https://interactivebrokers.github.io/index.html
