"""pytest settings shared by all tests."""


def pytest_configure(config):
    # Tests that reach Korean data sites (Naver, Daum, WiseReport) run locally only: CI uses -m "not network"
    # (constitution: technical constraints).
    config.addinivalue_line("markers", "network: needs live data sources; excluded from CI")
