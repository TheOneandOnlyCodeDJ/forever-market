from pathlib import Path

from fm import db, doctor, tsm_patch


def test_patch_tsm_applies_then_is_idempotent(tmp_path, monkeypatch):
    api = tmp_path / "API.lua"
    api.write_text(
        "local API = {}\n\nfunction API.GetCustomPrice(customPriceStr, itemString)\n"
        "\treturn CustomPrice.GetValue(customPriceStr, itemString)\nend\n\n-- tail\n")
    scanner = tmp_path / "ProfessionScanner.lua"
    scanner.write_text(
        "function private.CleanupThread()\n"
        "\t\t\tif not Profession.HasProfession(character, CraftInfoDB.GetProfession(craftString)) then\n"
        "\t\t\t\tprivate.removeCharactersTemp[character] = true\n"
        "\t\t\tend\nend\n")
    monkeypatch.setattr(tsm_patch, "API", api)
    monkeypatch.setattr(tsm_patch, "SCANNER", scanner)

    assert tsm_patch.run(write=True) == 0
    assert "function TSM_API.RegisterPriceSource" in api.read_text()
    assert 'character ~= "TSM-Ref"' in scanner.read_text()

    # second run changes nothing
    before = (api.read_text(), scanner.read_text())
    assert tsm_patch.run(write=True) == 0
    assert (api.read_text(), scanner.read_text()) == before


def test_patch_tsm_reports_when_anchor_is_gone(tmp_path, monkeypatch):
    api = tmp_path / "API.lua"
    api.write_text("-- rewritten by a future TSM release\n")
    scanner = tmp_path / "ProfessionScanner.lua"
    scanner.write_text("-- nothing to patch\n")
    monkeypatch.setattr(tsm_patch, "API", api)
    monkeypatch.setattr(tsm_patch, "SCANNER", scanner)
    results = dict(tsm_patch.apply(write=False))
    assert results["api"].startswith("failed") and results["scanner"].startswith("failed")


def test_doctor_offline_skips_token_and_flags_missing_bridge(tmp_path, monkeypatch):
    conn = db.connect(tmp_path / "d.db")
    monkeypatch.setattr(doctor, "TSM_API", tmp_path / "nope/API.lua")
    monkeypatch.setattr(tsm_patch, "API", tmp_path / "nope/API.lua")
    monkeypatch.setattr(tsm_patch, "SCANNER", tmp_path / "nope/Scanner.lua")
    monkeypatch.setattr(doctor, "BRIDGE", tmp_path / "nope/ForeverMarketBridge")
    monkeypatch.setenv("FM_DOCTOR_OFFLINE", "1")
    results = dict((name, level) for level, name, _ in doctor.checks(conn))
    assert results["token"] == "warn"
    assert results["bridge addon"] == "fail"
    assert results["tsm patch api"] == "fail"
    # counts still render so the output is useful with a fresh database
    assert results["rows item"] == "ok"
