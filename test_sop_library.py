"""Focused regression coverage for the controlled SOP training library."""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from contextlib import contextmanager

import app as app_module
import src.auth.middleware as auth_middleware
from scripts.publish_sops import validate_control_metadata


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "generated" / "sops"
EXPECTED = {
    "inventory-lot-control": ("ORA-APP-SOP-001", "Rev 02"),
    "order-corrections-cancellations": ("ORA-APP-SOP-002", "Rev 01"),
    "daily-fulfillment-pick-list": ("ORA-APP-SOP-003", "Rev 01"),
    "period-end-reporting": ("ORA-APP-SOP-004", "Rev 01"),
}


def user(authenticated=True, role="viewer"):
    return MagicMock(is_authenticated=authenticated, role=role, email="test@example.com")


@contextmanager
def signed_in_as(mock_user):
    with patch.object(app_module, "current_user", mock_user), patch.object(
        auth_middleware, "current_user", mock_user
    ):
        yield


def test_catalog_contains_exactly_four_controlled_drafts():
    catalog = json.loads((OUTPUT / "catalog.json").read_text())
    assert {sop["slug"] for sop in catalog} == set(EXPECTED)
    for sop in catalog:
        assert (sop["sop_id"], sop["revision"]) == EXPECTED[sop["slug"]]
        assert sop["status"] == "DRAFT FOR APPROVAL"
        assert sop["effective_date"] == "Upon approval"
        assert sop["approval_status"] == "Quality approval pending"
        assert "not yet released" in sop["document_status"]


def test_publisher_rejects_changed_draft_control_metadata():
    control = {
        "SOP ID": "ORA-APP-SOP-001", "Revision": "Rev 02",
        "Effective date": "Upon approval",
    }
    approval = {
        "Approved by": "Quality", "Approval date": "Pending",
        "Document status": "Editable master — approval copy not yet released",
    }
    banner = "CONTROLLED SOP — DRAFT FOR APPROVAL"
    assert validate_control_metadata("source.docx", control, approval, banner, "ORA-APP-SOP-001", "Rev 02") == "DRAFT FOR APPROVAL"
    assert validate_control_metadata(
        "period.docx", control, approval, "", "ORA-APP-SOP-001", "Rev 02",
        require_banner=False,
    ) == "DRAFT FOR APPROVAL"
    changes = (
        ("banner", "CONTROLLED SOP — APPROVED"),
        ("approver", "Operations"),
        ("approval date", "2026-09-17"),
        ("document status", "Approved release"),
        ("effective date", "2026-09-17"),
    )
    for field, changed in changes:
        changed_control = dict(control)
        changed_approval = dict(approval)
        changed_banner = banner
        if field == "banner":
            changed_banner = changed
        elif field == "approver":
            changed_approval["Approved by"] = changed
        elif field == "approval date":
            changed_approval["Approval date"] = changed
        elif field == "document status":
            changed_approval["Document status"] = changed
        else:
            changed_control["Effective date"] = changed
        try:
            validate_control_metadata(
                "source.docx", changed_control, changed_approval, changed_banner,
                "ORA-APP-SOP-001", "Rev 02",
            )
        except SystemExit:
            pass
        else:
            raise AssertionError(f"publisher accepted changed {field}")
    try:
        validate_control_metadata(
            "inventory.docx", control, approval, "", "ORA-APP-SOP-001", "Rev 02"
        )
    except SystemExit:
        pass
    else:
        raise AssertionError("publisher accepted a missing required draft banner")


def test_generated_web_and_pdf_metadata_are_consistent():
    for slug, (sop_id, revision) in EXPECTED.items():
        web = json.loads((OUTPUT / f"{slug}.json").read_text())
        pdf = (OUTPUT / f"{slug}.pdf").read_bytes()
        assert web["sop_id"] == sop_id
        assert web["revision"] == revision
        assert web["status"] == "DRAFT FOR APPROVAL"
        assert web["effective_date"] == "Upon approval"
        assert web["approval_status"] == "Quality approval pending"
        assert any(block["type"] == "warning" for block in web["blocks"])
        assert pdf.startswith(b"%PDF-")
        assert len(pdf) > 5000


def test_selected_sources_and_reconciled_workflow_wording():
    inventory = json.loads((OUTPUT / "inventory-lot-control.json").read_text())
    corrections = json.loads((OUTPUT / "order-corrections-cancellations.json").read_text())
    all_text = " ".join(
        block.get("text", "") + " " + " ".join(c for row in block.get("rows", []) for c in row)
        for sop in (inventory, corrections)
        for block in sop["blocks"]
    )
    assert inventory["source"] == "docs/Inventory_and_Lot_Control_SOP_Rev_02.docx"
    assert "05_Inventory_and_Lot_Control_SOP.docx" not in inventory["source"]
    assert "retired import workflows" in all_text
    daily = json.loads((OUTPUT / "daily-fulfillment-pick-list.json").read_text())
    daily_text = " ".join(block.get("text", "") for block in daily["blocks"])
    assert "Do not use New Orders or an XML import for daily fulfillment." in daily_text
    assert "It does not cover changing live order contents, hidden or direct database resets, bulk recovery controls" in all_text
    assert "archive" in all_text.lower()
    assert "Admin only" in all_text


def test_all_authenticated_roles_can_read_and_download_every_sop():
    client = app_module.app.test_client()
    for role in ("viewer", "operations", "admin"):
        with signed_in_as(user(role=role)):
            for slug in EXPECTED:
                assert client.get(f"/help/{slug}").status_code == 200
                content = client.get(f"/api/sops/{slug}")
                assert content.status_code == 200
                response = client.get(f"/sops/{slug}/download")
                assert response.status_code == 200
                assert response.headers["Content-Type"].startswith("application/pdf")
                assert response.headers["Content-Disposition"] == f'attachment; filename=Oracare_{slug}.pdf'
                assert response.data.startswith(b"%PDF-")


def test_signed_out_and_invalid_document_ids_are_rejected():
    client = app_module.app.test_client()
    with signed_in_as(user(authenticated=False)):
        assert client.get("/help.html").status_code == 302
        assert client.get("/help/inventory-lot-control").status_code == 302
        assert client.get("/sops/inventory-lot-control/download").status_code == 302
    with signed_in_as(user()):
        for path in (
            "/help/not-a-document",
            "/api/sops/not-a-document",
            "/sops/not-a-document/download",
            "/sops/..%2Fapp/download",
        ):
            assert client.get(path).status_code == 404


def test_sop_publish_endpoint_is_admin_only_and_runs_fixed_script():
    client = app_module.app.test_client()
    with signed_in_as(user(authenticated=False)):
        assert client.post("/api/sops/publish").status_code == 401
    with signed_in_as(user(role="viewer")):
        assert client.post("/api/sops/publish").status_code == 403
    with signed_in_as(user(role="operations")):
        assert client.post("/api/sops/publish").status_code == 403

    completed = MagicMock(returncode=0, stdout="Published 4 SOP drafts", stderr="")
    with signed_in_as(user(role="admin")), patch.object(
        app_module.subprocess, "run", return_value=completed
    ) as run:
        response = client.post("/api/sops/publish")

    assert response.status_code == 200
    assert response.get_json() == {
        "success": True,
        "message": "Published 4 SOP drafts",
    }
    assert run.call_args.args[0] == [
        app_module.sys.executable,
        str(ROOT / "scripts" / "publish_sops.py"),
    ]
    assert run.call_args.kwargs["cwd"] == str(ROOT)
    assert run.call_args.kwargs["timeout"] == 120
    assert "shell" not in run.call_args.kwargs


def test_sop_publish_endpoint_returns_bounded_validation_error():
    client = app_module.app.test_client()
    failed = MagicMock(
        returncode=1,
        stdout="",
        stderr="Traceback details that should not be returned\nsource.docx: missing required sections",
    )
    with signed_in_as(user(role="admin")), patch.object(
        app_module.subprocess, "run", return_value=failed
    ):
        response = client.post("/api/sops/publish")

    assert response.status_code == 422
    assert response.get_json() == {
        "success": False,
        "error": "source.docx: missing required sections",
    }


def test_sop_publish_endpoint_handles_timeout_and_concurrent_run():
    client = app_module.app.test_client()
    with signed_in_as(user(role="admin")), patch.object(
        app_module.subprocess,
        "run",
        side_effect=app_module.subprocess.TimeoutExpired("publish_sops.py", 120),
    ):
        response = client.post("/api/sops/publish")
    assert response.status_code == 504
    assert "timed out" in response.get_json()["error"]

    busy_lock = MagicMock()
    busy_lock.acquire.return_value = False
    with signed_in_as(user(role="admin")), patch.object(
        app_module, "_sop_publish_lock", busy_lock
    ):
        response = client.post("/api/sops/publish")
    assert response.status_code == 409
    assert response.get_json()["error"] == "SOP regeneration is already running."
    busy_lock.release.assert_not_called()


def test_sop_publish_endpoint_is_unavailable_in_deployment():
    client = app_module.app.test_client()
    with signed_in_as(user(role="admin")), patch.dict(
        app_module.os.environ, {"REPLIT_DEPLOYMENT": "1"}
    ), patch.object(app_module.subprocess, "run") as run:
        response = client.post("/api/sops/publish")

    assert response.status_code == 409
    assert "workspace only" in response.get_json()["error"]
    run.assert_not_called()


def test_help_reader_has_stable_links_toc_and_mobile_layout():
    page = (ROOT / "help.html").read_text()
    script = (ROOT / "static/js/sop-library.js").read_text()
    styles = (ROOT / "static/css/sop-library.css").read_text()
    assert 'id="sop-library"' in page
    assert 'id="publish-sops-button"' in page
    assert "data-admin-only" in page
    assert "fetch('/api/sops/publish'" in script
    assert "Publish the app to release these changes." in script
    assert "Controlled drafts — not approved releases." in page
    assert 'href="/help/${encodeURIComponent(sop.slug)}"' in script
    assert 'class="sop-toc"' in script
    assert "meta('Status', sop.status)" in script
    assert "meta('Document status', sop.document_status)" in script
    assert 'class="sop-warning"' in script
    assert "renderBlocks" in script
    assert "@media (max-width: 768px)" in styles
    assert "@media (max-width: 375px)" in styles
    assert "grid-template-columns: 1fr" in styles
    assert "min-height: 44px" in styles
    assert "overflow-x: auto" in styles