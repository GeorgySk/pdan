import pytest
from hypothesis import HealthCheck, settings

settings.register_profile(
    "default",
    deadline=None,
    suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow],
)
# run weekly in CI, takes several minutes
settings.register_profile(
    "thorough",
    parent=settings.get_profile("default"),
    max_examples=1000,
)


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(
    session: pytest.Session, exitstatus: pytest.ExitCode
) -> None:
    if exitstatus == pytest.ExitCode.NO_TESTS_COLLECTED:
        session.exitstatus = pytest.ExitCode.OK
