from pathlib import Path


CSS = (Path(__file__).resolve().parent / "static/css/global-styles.css").read_text()
VIOLATIONS_CSS = (
    Path(__file__).resolve().parent / "static/shipping-violations-alert.css"
).read_text()


def test_modal_contrast_tokens_cover_light_and_dark_themes():
    assert CSS.count("--modal-backdrop:") == 2
    assert CSS.count("--modal-border:") == 2
    assert CSS.count("--modal-shadow:") == 2


def test_all_shared_modal_systems_use_the_shared_backdrop():
    assert CSS.count("background-color: var(--modal-backdrop);") == 3
    assert CSS.count("backdrop-filter: blur(5px);") == 6

    assert "background-color: var(--modal-backdrop);" in VIOLATIONS_CSS
    assert VIOLATIONS_CSS.count("backdrop-filter: blur(5px);") == 2


def test_legacy_and_overlay_dialogs_have_defined_surfaces():
    legacy_surface = CSS.split(".modal > .modal-content {", 1)[1].split("}", 1)[0]
    overlay_section = CSS.split("MODAL OVERLAY & DIALOGS", 1)[1]
    overlay_surface = overlay_section.split(".modal-dialog {", 1)[1].split("}", 1)[0]

    for surface in (legacy_surface, overlay_surface):
        assert "background-color: var(--bg-primary);" in surface
        assert "border: 1px solid var(--modal-border);" in surface
        assert "box-shadow: var(--modal-shadow);" in surface


def test_violations_dialog_keeps_contrast_in_later_loaded_stylesheet():
    surface = VIOLATIONS_CSS.split(".violations-modal-content {", 1)[1].split("}", 1)[0]

    assert "background-color: var(--bg-primary);" in surface
    assert "border: 1px solid var(--modal-border);" in surface
    assert "box-shadow: var(--modal-shadow);" in surface