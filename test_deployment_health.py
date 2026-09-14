"""Regression coverage for the unauthenticated deployment health check."""

from pathlib import Path


APP = (Path(__file__).resolve().parent / "app.py").read_text()


def test_root_can_serve_public_landing_page_without_authentication():
    route_start = APP.index("@app.route('/')")
    route_end = APP.index("@app.route('/favicon.ico')", route_start)
    root_route = APP[route_start:route_end]

    assert "@login_required" not in root_route
    assert "page = 'index.html' if current_user.is_authenticated else 'landing.html'" in root_route