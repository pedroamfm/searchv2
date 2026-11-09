from unittest.mock import Mock

from meli.client import MercadoLibreClient


def test_client_retries_rate_limit(monkeypatch) -> None:
    monkeypatch.setenv("MELI_ACCESS_TOKEN", "test-token")
    client = MercadoLibreClient()
    limited, successful = Mock(status_code=429, headers={}), Mock(status_code=200, headers={})
    limited.url = successful.url = "https://api.mercadolibre.com/test"
    client.session.get = Mock(side_effect=[limited, successful])
    monkeypatch.setattr("meli.client.time.sleep", lambda _: None)
    assert client.get_response("/test") is successful
    assert client.session.get.call_count == 2
