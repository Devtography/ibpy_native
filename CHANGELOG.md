# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [v0.1.2] - 2020-05-20
`v0.1.2` is a minor hotfix releases fixed the issue found immediately after the 
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
- README section `Known issues`, `Development status` & `Contributions`.

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

[Unreleased]: https://github.com/Devtography/ibpy_native/compare/v0.1.2...HEAD
[v0.1.2]: https://github.com/Devtography/ibpy_native/compare/v0.1.2...v0.1.1
[v0.1.1]: https://github.com/Devtography/ibpy_native/compare/v0.1.0...v0.1.1
