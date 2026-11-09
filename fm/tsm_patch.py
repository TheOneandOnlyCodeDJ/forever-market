"""Re-apply our two local TradeSkillMaster patches after a TSM update wipes them.

Both are one-line/one-block insertions with stable anchors, so this writes them directly
instead of shelling out to `patch`. It is idempotent and safe to run every hour.
"""
from pathlib import Path

from fm import paths

TSM = Path(paths.CLIENT_DIR) / "Interface/AddOns/TradeSkillMaster"
API = TSM / "App/API.lua"
SCANNER = TSM / "LibTSMService/Source/Crafting/Internal/ProfessionScanner.lua"

API_MARK = "function TSM_API.RegisterPriceSource"
API_ANCHOR = "return CustomPrice.GetValue(customPriceStr, itemString)\nend\n"
API_BLOCK = '''
---Registers an external price source (forever-market local patch).
---@param key string The price source key
---@param label string The description shown in TSM
---@param callback fun(itemString: string): number? Returns the price in copper
function TSM_API.RegisterPriceSource(key, label, callback)
\tprivate.CheckCallMethod(key)
\tCustomString.RegisterSource("ForeverMarket", key, label, callback, CustomString.SOURCE_TYPE.NORMAL)
end
'''

SCANNER_MARK = 'character ~= "TSM-Ref"'
SCANNER_OLD = "\t\t\tif not Profession.HasProfession(character, CraftInfoDB.GetProfession(craftString)) then"
SCANNER_NEW = ('\t\t\t-- forever-market: injected craft rows belong to a synthetic character\n'
               '\t\t\tif character ~= "TSM-Ref" and not Profession.HasProfession(character, '
               'CraftInfoDB.GetProfession(craftString)) then')


def _status(path, marker):
    if not path.exists():
        return "missing"
    return "applied" if marker in path.read_text(errors="replace") else "absent"


def check():
    return [("api", _status(API, API_MARK)), ("scanner", _status(SCANNER, SCANNER_MARK))]


def apply(write=True):
    """Return [(name, result)] where result is applied/already/absent/failed."""
    results = []
    text = API.read_text(errors="replace") if API.exists() else None
    if text is None:
        results.append(("api", "missing"))
    elif API_MARK in text:
        results.append(("api", "already"))
    elif API_ANCHOR not in text:
        results.append(("api", "failed: anchor not found"))
    else:
        if write:
            API.write_text(text.replace(API_ANCHOR, API_ANCHOR + API_BLOCK, 1))
        results.append(("api", "applied" if write else "would apply"))

    text = SCANNER.read_text(errors="replace") if SCANNER.exists() else None
    if text is None:
        results.append(("scanner", "missing"))
    elif SCANNER_MARK in text:
        results.append(("scanner", "already"))
    elif SCANNER_OLD not in text:
        results.append(("scanner", "failed: anchor not found"))
    else:
        if write:
            SCANNER.write_text(text.replace(SCANNER_OLD, SCANNER_NEW, 1))
        results.append(("scanner", "applied" if write else "would apply"))
    return results


def run(write=True):
    for name, result in apply(write):
        print(f"tsm patch {name}: {result}")
    ok = {"applied", "already"}
    return 0 if all(r in ok for _, r in apply(write=False)) else 1
