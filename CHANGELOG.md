# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/Devtography/ibpy_native/compare/v0.1.4...HEAD
[v0.1.4]: https://github.com/Devtography/ibpy_native/compare/v0.1.4...v0.1.3 
[v0.1.3]: https://github.com/Devtography/ibpy_native/compare/v0.1.3...v0.1.2
[v0.1.2]: https://github.com/Devtography/ibpy_native/compare/v0.1.2...v0.1.1
[v0.1.1]: https://github.com/Devtography/ibpy_native/compare/v0.1.0...v0.1.1
