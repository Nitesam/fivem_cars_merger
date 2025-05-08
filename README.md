# fivem_cars_merger

A small Python utility to merge GTA-style car resources from multiple folders into a single, unified resource pack.  
It scans for car folders under a chosen level (e.g. `[L1]`), collects metadata, audio configs, SFX, and Lua name entries, then builds a consolidated `fxmanifest.lua`.

## Contents

- [config.ini](config.ini) – Configuration file:
  - `paths.base` points to the root directory containing `[Level]` folders.
  - `settings.level` sets the default level (e.g. `L1`).
- [unifier.py](unifier.py) – Main script to run the merge.

## Features

- Recursively copies:
  - `stream` subfolders
  - `.meta` files into a single `data/<car>/` tree
  - `audioconfig` and `sfx` directories
- Aggregates all `AddTextEntry` calls from Lua scripts into a single `vehicle_names.lua`
- Generates a complete `fxmanifest.lua` with appropriate data_file entries
- Logs operations to `operations.log` and cleans up original folders after merge

## Requirements

- Python 3.6+
- No external dependencies beyond the standard library

## Usage

1. Clone the repo:
   ```sh
   git clone https://github.com/yourname/fivem_cars_merger.git
   cd fivem_cars_merger
   ```
2. Edit [config.ini](config.ini) to point `paths.base` at your desktop (or wherever your `[L1]`, `[L2]`, … folders live) and set the default `level`.
3. Run the script:
   ```sh
   python unifier.py
   ```
4. Follow the prompt to choose a level (defaults to the one in `config.ini`).

The unified resource will be created in `C:\Users\Administrator\Desktop\<NAME>_Unified`.

## License

MIT License © Nitesam
