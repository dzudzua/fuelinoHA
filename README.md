# Fuelino

Custom Home Assistant integration for importing Fuelio backup CSV files.

## Version

Current integration version: `0.6.0`

## Installation

Recommended installation path:

1. Push this repository to GitHub
2. In Home Assistant, open HACS
3. Add this GitHub repository as a custom repository of type `Integration`
4. Install `Fuelino` from HACS
5. Restart Home Assistant

## MVP scope

- Reads Fuelio CSV backups from a local folder
- Creates sensors per discovered vehicle/file
- Parses refueling history with tolerant header matching
- Supports Fuelio's native sectioned export with `## Vehicle` and `## Log`
- Designed to become HACS-installable once the parser is validated on real exports

## Expected source files

The integration can read either:

- one specific CSV file
- one folder containing Fuelio CSV exports

When a folder is configured, it scans:

- `vehicle-*-sync.csv`
- `*.csv`

Each CSV file is treated as one vehicle dataset unless a recognizable vehicle name is present in the file.

## Local development

Copy `custom_components/fuelio` into your Home Assistant config directory and add the integration from the UI.

Recommended next step: drop a few real Fuelio backup files into a test folder and tune the parser against them.

## Home Assistant usage

Recommended workflow for your own Home Assistant:

1. Copy this integration to `/config/custom_components/fuelio/`
2. Place your Fuelio export into Home Assistant storage, for example `/config/fuelio/hjundaj.csv`
3. Add the integration from the Home Assistant UI
4. In setup, enter either the full CSV path or the folder path

If you keep replacing the same CSV file with a newer export, the integration will refresh it on the configured scan interval.

If you install via HACS instead of manual copy, only steps 2-4 are needed after installation.

## Upload panel

The integration now includes a built-in upload page inside Home Assistant.

- Open `/api/fuelio/upload-page` in your Home Assistant browser session
- Alias URL `/fuelio-upload` should also work
- Pick a CSV file from your phone or computer
- The file is stored into the Home Assistant config folder under `fuelino/`
- Loaded Fuelio entries are refreshed automatically after upload

## In-Integration Actions

Fuelio now also exposes helper buttons directly inside Home Assistant:

- `Open upload help`: shows the upload URL and the configured source path
- `Reload data`: refreshes Fuelio data immediately

When the configured source path is a folder, Fuelio now prefers the newest CSV per vehicle.

## Dashboard Example

A ready-to-adapt Lovelace example is available in:

- `examples/lovelace_fuelio_dashboard.yaml`

Rename entity ids there to match your own vehicle slug if needed.

## GitHub publishing

Minimal flow:

```powershell
git add .
git commit -m "Initial Fuelino integration"
git branch -M main
git remote add origin https://github.com/<your-user>/<your-repo>.git
git push -u origin main
```

Then add the repository URL in HACS as a custom integration source.

Do not commit your real Fuelio exports to a public repository. Keep personal CSV backups out of git and only point Home Assistant to local files stored inside your HA config.

## Changelog

- `0.6.0`: added advanced fuel analytics for consumption, fill cadence, monthly comparisons, price trends, and location/station summaries
- `0.5.3`: added missing HACS-friendly issue tracker metadata to the integration manifest
- `0.5.2`: made the upload-help notification include a clickable upload link
- `0.5.1`: added clearer Home Assistant icons for Fuelio sensors
- `0.5.0`: expanded CSV-backed history with richer recent-fill details, monthly average price, and more historical summary attributes
- `0.4.1`: added historical recent-fill and monthly-summary attributes for CSV-backed history views
- `0.4.0`: added richer city, station, 30-day and dashboard-focused insights
- `0.3.1`: fixed parser dataclass field ordering for Home Assistant startup
- `0.3.0`: added richer CSV insights like monthly cost, full-tank metrics, city and weather-based details
- `0.2.1`: relative source paths now resolve inside the Home Assistant config directory
- `0.2.0`: added in-integration helper buttons and improved newest-file selection in folder mode
- `0.1.19`: fixed upload refresh crash caused by non-coordinator data in runtime storage
- `0.1.18`: fixed CSV upload crash caused by missing Path import
- `0.1.17`: added token-based upload fallback to improve remote upload compatibility
- `0.1.16`: improved upload error handling and diagnostics
- `0.1.15`: moved upload page to explicit API route for better compatibility with HA routing and Nabu Casa
- `0.1.14`: fixed unauthorized access to the upload page while keeping uploads protected
- `0.1.13`: switched upload UI to a stable internal authenticated page at `/fuelio-upload`
- `0.1.12`: switched upload UI back to authenticated custom panel
- `0.1.11`: switched CSV upload UI to a compatible iframe sidebar panel
- `0.1.10`: fixed frontend panel API compatibility for CSV upload
- `0.1.9`: fixed Home Assistant sidebar panel registration for CSV upload
- `0.1.8`: added direct CSV upload panel inside Home Assistant
- `0.1.7`: fixed Home Assistant device registration compatibility
- `0.1.6`: minimized package init imports to troubleshoot config flow loading
- `0.1.5`: lighter package import path to help config flow loading
- `0.1.4`: simplified config flow compatibility, clearer manifest metadata
- `0.1.3`: relaxed config flow source validation
- `0.1.2`: added `fuelio.reload` service
- `0.1.1`: parser and sensor improvements for real Fuelio exports
- `0.1.0`: initial custom integration MVP

## Tests

The parser regression tests use the sample export in the project root:

```powershell
python -m unittest tests.test_parser
```
