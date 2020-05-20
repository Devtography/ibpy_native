# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/Devtography/ibpy_native/compare/v0.1.1...HEAD
[v0.1.1]: https://github.com/Devtography/ibpy_native/compare/v0.1.0...v0.1.1
