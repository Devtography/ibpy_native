# IbPy Native - Interactive Brokers Native Python API

A fully asynchronous framework for using the native Python version of
Interactive Brokers API.

The whole framework is built on Python's built in `asyncio` and `queue` modules,
no event emitter nor any other heavy 3rd party library. The only 3rd party
package used is `pytz` for timezone related things. In this way the framework
is being kept as native Python as possible and the performance shouldn't get
slowed down due to the libraries used.

Additionally, most if not all public classes implement their corresponding
interface. Therefore, it's easy to implement a customised version for most of
the classes. Hence, mocking the API calls/data returns for backtest can be
easily done, and you should be able to use the same set of strategy code on both
simulate and live trading sessions.

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

For more, please have a look on the sample scripts in `samples` folder. There's
one script that shows how to request for historical tick data atm, but there
will be more as I keep developing my own system based on this framework.

In the meantime, you may want to read the doc and checkout the unittest for the
ideas of how the APIs work.

_**Do make sure you are using a paper account while running the unittest cases,
as some of those tests do place real orders to IB and orders will get filled.**_

## System requirements
- Python >= 3.7; Pervious versions are not supported (development is based on 
Python 3.7.9)
- _Included IB API version - `9.79.01`_

## Development status (a.k.a. Words from developers)
Although the project is under the stage of active development, up until now
(`v1.0.0`) it focuses on working with FX, stock & future contracts from IB.
Other security types (e.g. options) may work but those are not yet tested.

This project is not providing full features of IB API yet, but `v1.0.0` is
already capable to retrieve & manage account and orders data, placing and
cancelling the orders, so as requesting historical and live tick data. More
features will be supported if my internal trading system needs (that's the
highest priority), or by request on the issues board.

## Contributions
Contributions via pull requests are welcome and encouraged. If there's any 
feature you think is missing, please don't hesitate to implement yourself and 
make a pull request :)

_Please follow the [Google Python Style Guide] as much as possible for all the
code included in your pull request. Otherwise the pull request may be rejected._

## Donation
This framework has spent me a whole year to develop from scratch until the first
stable release (`v1.0.0`). Hopefully you'll find this framework useful as much
as I do. 

If you wanna support my work, please consider [donate/sponsor] me. Thus I can
keep on investing time to further develop the framework alongside my job and
other projects.

## Author
[Wing Chau] [@Devtography]

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
[donate/sponsor]: https://github.com/sponsors/iamWing
[Wing Chau]: https://github.com/iamWing
[@Devtography]: https://github.com/Devtography
[TWS API Non-Commercial License]: https://interactivebrokers.github.io/index.html
