# IbPy Native - Interactive Brokers Native Python API

A fully asynchronous framework for using the native Python version of
Interactive Brokers API.

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
import pytz
from ibapi import contract as ib_contract
from ibpy_native import bridge as ibpy_bridge

# Set the timezone to match the timezone specified in TWS or IB Gateway when login
# Default timezone - 'America/New_York'
ibpy_native.IBBridge.set_timezone(pytz.timezone('America/New_York'))


# Connect to a running TWS or IB Gateway instance
bridge = ibpy_bridge.IBBridge(
    host='127.0.0.1', port=4001, client_id=1, auto_conn=True
)

# Search the US stock contract of Apple Inc.
aapl_contract = ib_contract.Contract()
aapl_contract.symbol = 'AAPL'
aapl_contract.secType = 'STK'
aapl_contract.exchange = 'SMART'
aapl_contract.currency = 'USD'

# Sometimes just defining the `Contract` object yourself is enough to match an
# unique contract on IB and make requests for the contract, but performing a
# search can ensure you get the valid & unique contract to work with.
search_results = await bridge.search_detailed_contracts(
    contract=aapl_contract
)

# Ask for the earliest available data point of AAPL
head_timestamp = await bridge.get_earliest_data_point(
    contract=search_results[0].contract
)
```

## System requirements
- Python >= 3.7; Pervious versions are not supported (development is based on 
Python 3.7.7)
- _Included IB API version - `9.79.01`_

## Development status (a.k.a. Words from developers)
Although the project is under the stage of active development, up until now
(`v0.2.0`) it focuses on working with FX, stock & future contracts from IB.
Other security types (e.g. options) may work but those are not yet tested.

This project is not providing full features of IB API yet, but basic features 
like retrieving data of contracts from IB, getting live & historical ticks are
ready to be used. Remaining features like retrieving account details, place & 
modify orders are planned to be implemented prior the first stable release 
(`v1.0.0`), but there is no estimated timeline for those atm, as the project is
being developed alongside Devtography internal algo-trading program, so as my
daily job. For now, the features will be developed and released when needed.

## Contributions
Contributions via pull requests are welcome and encouraged. If there's any 
feature you think is missing, please don't hesitate to implement yourself and 
make a pull request :)

_Please follow the [Google Python Style Guide] as much as possible for all the
code included in your pull request. Otherwise the pull request may be rejected._

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

[Google Python Style Guide]: https://google.github.io/styleguide/pyguide.html
[TWS API Non-Commercial License]: https://interactivebrokers.github.io/index.html
