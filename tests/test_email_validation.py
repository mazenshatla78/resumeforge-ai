from backend.services.email_validation.email_validator import validate_email
from backend.services.email_validation.disposable_domains import is_disposable, count
from backend.services.email_validation.consumer_providers import is_consumer_provider


def test_consumer_provider():
    r = validate_email("user@gmail.com", check_mx=False)
    assert r.status == "valid_consumer"
    assert r.is_consumer is True


def test_business_domain():
    r = validate_email("jane@acme.io", check_mx=False)
    assert r.status == "valid_custom_domain"
    assert r.is_business_candidate is True


def test_disposable_rejected():
    r = validate_email("x@mailinator.com", check_mx=False)
    assert r.status == "disposable_domain"


def test_invalid_email():
    r = validate_email("not-an-email", check_mx=False)
    assert r.status == "invalid_email"


def test_disposable_list_loaded():
    assert count() > 10000


def test_is_disposable_subdomain():
    assert is_disposable("mailinator.com")
