# FuelinoHA

FuelinoHA is a custom Home Assistant project for importing Fuelio backup CSV files through the Fuelino integration.

![Fuelino preview](assets/fuelino-showcase.png)

## Version

Current integration version: `0.10.2`

## What Fuelino supports

- Fuelio CSV import from a local file or folder
- Fuelio CSV import from a Dropbox / remote CSV URL
- automatic vehicle discovery from Fuelio exports
- fuel statistics and driving analytics
- city, station, weather and history insights
- non-fuel costs from Fuelio `Costs` and `CostCategories`
- ready-to-adapt Lovelace dashboard example

## Recommended installation

1. Push this repository to GitHub
2. In Home Assistant, open HACS
3. Add this GitHub repository as a custom repository of type `Integration`
4. Install `Fuelino`
5. Restart Home Assistant

## First use

Recommended workflow:

1. Put your Fuelio export into Home Assistant storage, for example `/config/fuelino/`
2. Add the `Fuelio` integration from the Home Assistant UI
3. Choose a source type:
   - local CSV file or folder
   - Dropbox / remote CSV URL
4. If using a local folder, Fuelino will prefer the newest CSV per vehicle
5. If using Dropbox, prefer a stable shared file link to one CSV such as `vehicle-1-sync.csv`

If you keep replacing the same export or keep uploading newer CSV files into the folder, Fuelino will refresh on the configured scan interval.

## Upload page

Fuelino includes a built-in upload page inside Home Assistant.

- Open `/api/fuelio/upload-page` in your Home Assistant session
- Alias URL `/fuelio-upload` should also work
- Pick a CSV file from your phone or computer
- The file is stored into the Home Assistant config folder under `fuelino/`

Note:
- local-network use is the most reliable workflow for the upload page

## In-Integration actions

Fuelio exposes helper buttons inside Home Assistant:

- `Open upload help`
- `Reload data`

## Dashboard example

A ready-to-adapt Lovelace example is available in:

- `examples/lovelace_fuelio_dashboard.yaml`

It includes:

- fuel overview
- cost and trend section
- driving profile and consumption
- station and city insights
- service and other vehicle expenses
- recent fill history
- monthly summary

Rename entity ids there to match your own vehicle slug if needed.

## Source files

Fuelino can read either:

- one specific CSV file
- one folder containing Fuelio CSV exports
- one remote CSV URL, for example a Dropbox shared file link

When a folder is configured, it scans:

- `vehicle-*-sync.csv`
- `*.csv`

Each CSV file is treated as one vehicle dataset unless a recognizable vehicle name is present in the file.

## Dropbox links

FuelinoHA supports a remote CSV URL mode intended for simple Dropbox-based setups.

Recommended approach:

1. Open your Fuelio Dropbox backup folder
2. Share one concrete CSV file, for example `vehicle-1-sync.csv`
3. Paste that shared link into the integration
4. Fuelino will normalize Dropbox file links for direct download automatically

This is best when Fuelio keeps updating the same file name.

## Privacy

Do not commit your real Fuelio exports to a public repository.
Keep personal CSV backups out of git and only point Home Assistant to local files stored inside your HA config.

## Tests

```powershell
python -m unittest tests.test_parser
python -m compileall custom_components\fuelio tests examples
python tools\inspect_fuelio_export.py hjundaj-1-2026-04-19_12-09.csv
```

## Changelog

- `0.10.2`: merged local path and Dropbox URL setup into one integration form
- `0.10.1`: fixed and cleaned Czech translations so the integration can be used in Czech or English cleanly
- `0.10.0`: added a new source-type setup flow with Dropbox / remote CSV URL support
- `0.9.4`: added category-specific expense totals for service, wash, registration, parking, tolls, and insurance
- `0.9.3`: added a local export-inspection tool alongside diagnostics and real-export validation
- `0.9.2`: added diagnostics support for config-entry troubleshooting and release validation
- `0.9.1`: added TripLog parsing, trip sensors, better service highlights, and a smarter expense dashboard
- `0.9.0`: release-ready polish, richer dashboard including non-fuel expenses, and clearer first-use documentation
- `0.7.1`: changed upload-help notifications to use a full Home Assistant URL when available
- `0.7.0`: added parsing of Fuelio Costs/CostCategories plus non-fuel expense sensors and attributes
- `0.6.1`: added Czech translations and a richer dashboard example for the new analytics
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
