# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [v1.0.4] - 2021-03-15
Hotfix `IBBridge.req_historical_ticks`.

### Fixed
- Issue of the recursive historical ticks requests won't have its' next start
  time advanced when IB returns only 1 tick which is earlier than the start
  time requested for that iteration of request.

## [v1.0.3] - 2021-03-14
Hotfix `IBBridge.req_historical_ticks`.

### Fixed
- Issue of end time specified for `IBBridge.req_historical_ticks` get ignored
  when fetching expired futures contract.

## [v1.0.2] - 2021-03-09
Minor release focuses on bug fixes.

### Added
- Properties `host`, `port`, and `client_id` on interface
  `ibpy_native.interfaces.IBBridge` and its' implementation
  `ibpy_native.IBBridge`.
- Limits value of argument `client_id` on `ibpy_native.IBBridge` to `9999` max.

### Changed
- `ibpy_native.IBBridge.req_historical_ticks()` to enhance its' reliability and
  accuracy on filtering out ticks received which shouldn't be included in the
  result of the request.

### Fixed
- Type hint of return type `ibpy_native.utils.datatype.ResHistoricalTicks`.
- Error of error code `10187 - "Invalid starting time (future data request)"`
  raises from `ibpy_native.IBBridge.req_historical_ticks()` at the end of the
  task when argument `end` is `None`.
- Issue of request will hang up on clients under the condition of multiple
  clients submitted the same type of request to the same TWS / IB Gateway
  instance and appear to have used the same request / ticker ID.

## [v1.0.1] - 2021-03-07
Minor enhancement on function `IBBridge.req_historical_ticks` to provide option
for much shorter process time on requests starting from the earliest available
data point.

### Added
- Optional argument `daily_data_starting_point` on function
  `IBBridge.req_historical_ticks`.

### Changed
- Data returned from `IBBridge.req_historical_ticks` to include the next start
  time for the next API request when the task is not finished yet.

## [v1.0.0] - 2021-02-28
`v1.0.0` is the first usable release of the framework. Accounts & orders
management features are now implemented, so as placing orders. It's a usable
framework for actual trading as of this release. However, it's NOT compatible
with pervious versions as a lot of the functions got revamped, including the
functions for fetching the historical data.

### Added
- Support of requesting and managing account & portfolio data.
- Support of requesting active orders & orders management (including order
  placing, cancellation, and order status updates, etc..).
- Connection status event listener to notify the connection status between
  the client program and IB TWS/Gateway.
- Handling for unexpected connection drops.
  - Resources will be released and on-going tasks will all be terminated on
    disconnected.
- Corresponding interfaces for most if not all public classes for easy mocking,
  so it's gonna be easy to backtest the strategies and use the same set of
  strategy code for both backtest and live trading.

### Changed
- Reordered the grouping of packages and modules (breaking change).
- `IBBridge.req_historical_ticks` now works as an async iterator.

### Removed
- All deprecated functions.
- Deprecated script `cmd/fetch_us_historical_ticks.py`.

## [v0.2.0] - 2020-09-02
`v0.2.0` is a minor release refactored most of the project to adopt async/await
syntax, added support of streaming live "tick-by-tick" data from IB, and
restructured the project.

### Added
- Module `ibpy_native.utils.datatype` to hold `Enum` or `TypedDict` for types of
  function arguments or return objects.
- Listener to receive system notifications from IB (via
  `ibpy_native.interfaces.listeners.NotificationListener`) in public class
  `ibpy_native.bridge.IBBridge`.
  - Corresponding setter `set_on_notify_listener(listener)`.
- Function `ibpy_native.bridge.IBBridge.search_detailed_contracts(contract)` to
  search for contracts with complete details from IB's database. This newly
  implemented function is recommended to replace the deprecated functions
  `get_us_stock_contract(symbol)` & `get_us_future_contract(symbol,
  contract_month)` in `IBBridge`.
- Feature of streaming live "tick-by-tick" data from IB via functions
  `ibpy_native.bridge.IBBridge.stream_live_ticks(contract, listener, 
  tick_type=ibpy_native.utils.datatype.LiveTicks.LAST)` and
  `ibpy_native.bridge.IBBridge.stop_live_ticks_stream(stream_id)`.

### Changed
- Existing code to align the code style with 
  [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html#s3.16-naming).
- Module files location to group them in corresponding sub-packages.
- Name of classes, variables, and functions to get rid of the prepended double
  underscore and prepended single underscore for all non-public classes/members
  to mark for internal usage.
- Mechanism of internal queue management.
- Minimum Python version requirement to `3.7` as some of the built-in feature of
  `3.7` is being used in the project.

### Deprecated
- Function `ibpy_native.bridge.IBBridge.get_us_stock_contract(symbol)`.
- Function `ibpy_native.bridge.IBBridge.get_us_future_contract(symbol, contract_month)`.
- Script `cmd/fetch_us_historical_ticks.py`. This script might be updated to
  work with the refactored functions in future release, but it's not usable for
  now.

### Removed
- Argument `timeout` on all APIs implemented (use function 
  `asyncio.wait_for(aw, timeout, *, loop=None)` for timeout instead if needed).

## [v0.1.4] - 2020-06-01
`v0.1.4` is a hotfix release addressing the issue of various errors which will 
be raised while fetching the historical ticks.

### Added
- Command option `--timeout` to script `cmd/fetch_us_historical_ticks.py`.
- Docstring to files in `/ibpy_native`.
- `.pylintrc` file to control the Pylint behaviours.

### Changed
- The parameter `attempts` of `IBBridge.get_historical_ticks` now accepts value
`-1` to loop the IB API `reqHistoricalTicks` until all available ticks for the
specified period are fetched.

### Removed
- `README` section `Known issues` as the only issue documented there has been
fixed.

### Fixed
- Issue of `IBBridge.get_historical_ticks` will raise the error `code: 200 - No
security definition has been found for the request` in the middle of ticks
fetching.
- Issue of `IBBridge.get_historical_ticks` cannot finish fetching all available
ticks of a future contract as IB keeps returning "Duplicate ticker ID" when
fetching near the earliest available data point.
- Incorrect time comparison between native datetime object `end` with aware
datetime object `head_timestamp` in `IBBridge.get_historical_ticks`.

## [v0.1.3] - 2020-05-20
`v0.1.3` is a minor release includes a script to fetch historical ticks of 
US contracts for quick use.

### Added
- script `cmd/fetch_us_historical_ticks.py` to fetch historical ticks,

### Changed
- `README` to introduce the usage of the newly included script.

### Notes
- version in `setup.py` remains as `0.1.2` as there is nothing changed for 
files included in the package released.

## [v0.1.2] - 2020-05-20
`v0.1.2` is a minor hotfix release fixed the issue found immediately after the 
release of `v0.1.1`.

### Added
- Reminder to use newest version in `README`.

### Fixed
- Issue of the `next_end_time` defined in `IBClient.fetch_historical_ticks` 
won't change to earlier `0` or `30` minutes if the current `next_end_time` is 
already at `hh:00:00` or `hh:30:00` by minus 30 minutes directly.

## [v0.1.1] - 2020-05-20
`v0.1.1` is a minor hotfix release fixed the issue of 
`IBClient.fetch_historical_ticks` returns with `finished` mark as `True` 
unexpectedly.

### Added
- `README` section `Known issues`, `Development status` & `Contributions`.

### Changed
- `start` is no longer an optional parameter for function 
`IBClient.fetch_historical_ticks` as the start time is needed to determine if 
it has fetched as many ticks as it should from IB.
- The earliest available data point will be passed to function 
`IBClient.fetch_historical_ticks` as `start` value if function 
`IBBridge.get_historical_ticks` has value `None` of its' parameter `start` to 
accomplish the changes made in `IBClient.fetch_historical_ticks` described 
above.

### Fixed
- Issue of `IBClient.fetch_historical_ticks` breaks the API request loop and 
returns with `finished` mark as `True` unexpectedly while IB returns less than 
1000 records but there're more historical ticks those should be fetched 
in next request.

[Unreleased]: https://github.com/Devtography/ibpy_native/compare/v1.0.4...HEAD
[v1.0.4]: https://github.com/Devtography/ibpy_native/compare/v1.0.4...v1.0.3
[v1.0.3]: https://github.com/Devtography/ibpy_native/compare/v1.0.3...v1.0.2
[v1.0.2]: https://github.com/Devtography/ibpy_native/compare/v1.0.2...v1.0.1
[v1.0.1]: https://github.com/Devtography/ibpy_native/compare/v1.0.1...v1.0.0
[v1.0.0]: https://github.com/Devtography/ibpy_native/compare/v1.0.0...v0.2.0
[v0.2.0]: https://github.com/Devtography/ibpy_native/compare/v0.2.0...v0.1.4
[v0.1.4]: https://github.com/Devtography/ibpy_native/compare/v0.1.4...v0.1.3 
[v0.1.3]: https://github.com/Devtography/ibpy_native/compare/v0.1.3...v0.1.2
[v0.1.2]: https://github.com/Devtography/ibpy_native/compare/v0.1.2...v0.1.1
[v0.1.1]: https://github.com/Devtography/ibpy_native/compare/v0.1.0...v0.1.1
