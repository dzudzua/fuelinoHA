# Fuelino

Custom Home Assistant integration for importing Fuelio backup CSV files.

## Version

Current integration version: `0.1.14`

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

- Open `/fuelio-upload` in your Home Assistant browser session
- Pick a CSV file from your phone or computer
- The file is stored into the Home Assistant config folder under `fuelino/`
- Loaded Fuelio entries are refreshed automatically after upload

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
