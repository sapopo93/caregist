"""Contracts for account-state reads on provider pages."""

from api.middleware.auth import validate_billing_identity
from api.routers.providers import router


def test_monitor_status_does_not_consume_product_allowance():
    route = next(
        route
        for route in router.routes
        if route.path == "/api/v1/providers/{slug}/monitor-status" and "GET" in route.methods
    )

    assert any(
        dependency.call is validate_billing_identity
        for dependency in route.dependant.dependencies
    )
