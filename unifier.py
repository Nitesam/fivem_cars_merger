import os, shutil, logging, configparser
from pathlib import Path
import sys, time

if getattr(sys, 'frozen', False):
    app_dir = Path(sys.executable).parent
else:
    app_dir = Path(__file__).parent

# load config from that folder
cfg = configparser.ConfigParser()
cfg.read(app_dir / 'config.ini')

if not cfg:
    print("ERROR: config.ini not found.")
    print("Please check your config.ini.")
    print("Exiting in 5 seconds...")
    time.sleep(5)
    sys.exit(1)

if not cfg.has_section('paths'):
    print("ERROR: config.ini does not have a [paths] section.")
    print("Please check your config.ini.")
    print("Exiting in 5 seconds...")
    time.sleep(5)
    sys.exit(1)

if not cfg.has_option('paths', 'base'):
    print("ERROR: config.ini does not have a 'base' option under [paths].")
    print("Please check your config.ini.")
    print("Exiting in 5 seconds...")
    time.sleep(5)
    sys.exit(1)

BASE    = Path(cfg['paths']['base'])
DEFAULT = cfg['settings'].get('level', 'L1')

if not BASE.exists() or not BASE.is_dir():
    print(f"ERROR: Base path '{BASE}' not found or is not a directory.")
    print("Please check your config.ini.")
    print("Exiting in 5 seconds...")
    time.sleep(5)
    sys.exit(1)

def prompt_level():
    print("==========================================")
    print("  Car Resource Unifier")
    print("==========================================")
    print("Base path:", BASE)
    available_levels = [d.name.strip("[]") for d in BASE.iterdir() if d.is_dir() and d.name.startswith('[') and d.name.endswith(']')]
    if not available_levels:
        print("ERROR: No valid level folders (e.g., '[L1]') found in the base path.")
        print("Exiting in 5 seconds...")
        time.sleep(5)
        sys.exit(1)
    print("Available levels:", available_levels)
    lvl = input(f"Enter level to unify [{DEFAULT}]: ").strip()
    return lvl or DEFAULT

LEVEL   = None
SRC_ROOT= None
UNIFIED = None
LOG_FILE= None

# map .meta → fxmanifest data_file type
META_TYPES = {
    'handling.meta':         'HANDLING_FILE',
    'vehicles.meta':         'VEHICLE_METADATA_FILE',
    'carcols.meta':          'CARCOLS_FILE',
    'carvariations.meta':    'VEHICLE_VARIATION_FILE',
    'vehiclelayouts.meta':   'VEHICLE_LAYOUTS_FILE',
}

# new audio‐type map – only include .rel files, drop .nametable types
AUDIO_TYPES = {
    '.dat10.rel':  'AUDIO_SYNTHDATA',
    '.dat151.rel': 'AUDIO_GAMEDATA',
    '.dat54.rel':  'AUDIO_SOUNDDATA',
}

# FX manifest template
FX_TMPL = """fx_version 'cerulean'
games {{'gta5'}}

{datas}

files {{
{files}
}}

client_script 'vehicle_names.lua'
"""

NAMES = []

def ensure_empty(dir: Path):
    if dir.exists():
        shutil.rmtree(dir)
    dir.mkdir(parents=True)

def setup_logging():
    ensure_empty(UNIFIED)
    logging.basicConfig(
        filename=str(LOG_FILE),
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logging.info("=== Starting merge operation ===")

def gather_names(car_src: Path):
    # scan all .lua under this car folder for AddTextEntry calls
    for lua in car_src.rglob("*.lua"):
        with open(lua, encoding="utf-8") as f:
            for line in f:
                if "AddTextEntry" in line:
                    NAMES.append(line.strip())
                    logging.info(f"Found name entry in {lua}: {line.strip()}")

def copy_car(car: str):
    car_src = SRC_ROOT / car
    logging.info(f"Processing car folder: {car_src}")

    gather_names(car_src)

    src_stream = car_src / "stream"
    if src_stream.is_dir():
        dst = UNIFIED / "stream" / car
        shutil.copytree(src_stream, dst)
        logging.info(f"Copied stream {src_stream} → {dst}")
    # data
    dst_data = UNIFIED / "data" / car
    dst_data.mkdir(parents=True, exist_ok=True)
    for root, _, files in os.walk(car_src):
        for f in files:
            if f.endswith(".meta"):
                src_f = Path(root) / f
                dst_f = dst_data / f
                dst_f.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(src_f, dst_f)
                logging.info(f"Copied meta {src_f} → {dst_f}")
    # audioconfig + sfx
    for sub in ("audioconfig", "sfx"):
        src_dir = car_src / sub
        if src_dir.is_dir():
            dst_dir = UNIFIED / sub / car
            shutil.copytree(src_dir, dst_dir)
            logging.info(f"Copied {sub} {src_dir} → {dst_dir}")

def write_unified_names():
    if not NAMES:
        return
    out = UNIFIED / "vehicle_names.lua"
    with open(out, "w", encoding="utf-8") as f:
        f.write("Citizen.CreateThread(function()\n")
        for entry in NAMES:
            if entry.strip().startswith("function AddTextEntry"):
                continue
            f.write(f"    {entry}\n")
        f.write("end)\n")
    logging.info(f"Created unified names script: {out}")

def build_fxmanifest():
    datas = []
    files = []

    # META entries
    for car in CARS:
        datas.append(f"-- {car} meta")
        files.append(f"-- {car} meta")
            
        for meta_name, dtype in META_TYPES.items():
            meta_path = UNIFIED / "data" / car / meta_name
            if meta_path.exists():
                rel = f"data/{car}/{meta_name}"
                datas.append(f"data_file '{dtype}' '{rel}'")
                files.append(f"  '{rel}'")

    # AUDIO data_file entries – use .dat placeholder for .rel files
    for car in CARS:
        base = UNIFIED / "audioconfig" / car
        if base.is_dir():
            datas.append(f"-- {car} audioconfig")
            files.append(f"-- {car} audioconfig")
            for f in base.iterdir():
                name = f.name
                if name.endswith('.dat10.rel'):
                    dtype = 'AUDIO_SYNTHDATA'
                    placeholder = name.rsplit('.dat10.rel', 1)[0] + '.dat'
                elif name.endswith('.dat151.rel'):
                    dtype = 'AUDIO_GAMEDATA'
                    placeholder = name.rsplit('.dat151.rel', 1)[0] + '.dat'
                elif name.endswith('.dat54.rel'):
                    dtype = 'AUDIO_SOUNDDATA'
                    placeholder = name.rsplit('.dat54.rel', 1)[0] + '.dat'
                else:
                    continue

                rel_dat = f"audioconfig/{car}/{placeholder}"
                datas.append(f"data_file '{dtype}' '{rel_dat}'")

                rel_rel = f"audioconfig/{car}/{name}"
                files.append(f"  '{rel_rel}'")

    # AUDIO_WAVEPACK entries
    for car in CARS:
        sfx_car = UNIFIED / "sfx" / car
        if sfx_car.is_dir():
            datas.append(f"-- {car} sfx")
            for pack in sfx_car.iterdir():
                if pack.is_dir():
                    rel = f"sfx/{car}/{pack.name}"
                    datas.append(f"data_file 'AUDIO_WAVEPACK' '{rel}'")

    # SFX file listings
    sfx_base = UNIFIED / "sfx"
    if sfx_base.is_dir():
        files.append(f"-- {car} sfx")
        for root, _, fnames in os.walk(sfx_base):
            for f in fnames:
                rel = Path(root).joinpath(f).relative_to(UNIFIED).as_posix()
                files.append(f"  '{rel}'")

    fx = FX_TMPL.format(
        datas="\n".join(datas),
        files=",\n".join(files)
    )
    (UNIFIED / "fxmanifest.lua").write_text(fx, encoding="utf-8")
    logging.info("Generated fxmanifest with corrected audio placeholders")

if __name__ == "__main__":
    LEVEL    = prompt_level()
    SRC_ROOT = BASE / f"[{LEVEL}]"
    UNIFIED  = BASE / f"{LEVEL}_Unified"
    LOG_FILE = UNIFIED / "operations.log"

    CARS = [
        d.name for d in SRC_ROOT.iterdir()
        if d.is_dir() and not (d / '.fxap').is_file()
    ]

    setup_logging()
    for car in CARS:
        copy_car(car)
        src_car = SRC_ROOT / car
        try:
            shutil.rmtree(src_car)
            logging.info(f"Deleted original folder: {src_car}")
        except Exception as e:
            logging.error(f"Failed to delete original folder {src_car}: {e}")

    write_unified_names()
    build_fxmanifest()
    logging.info("=== Merge operation completed ===")

    print(f"\n✅ Unified resource created at: {UNIFIED}")
    input("Press ENTER to exit…")
    sys.exit(0)