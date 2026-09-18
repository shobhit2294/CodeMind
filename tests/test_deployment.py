import pytest
from fastapi.testclient import TestClient
import backend.main as main


def test_render_host_and_browser_origin(monkeypatch, tmp_path):
    monkeypatch.setenv('RENDER_EXTERNAL_HOSTNAME', 'codemind-gzke.onrender.com')
    dist = tmp_path / 'frontend' / 'dist'
    dist.mkdir(parents=True)
    (dist / 'index.html').write_text('CodeMind frontend', encoding='utf-8')
    monkeypatch.setattr(main, 'ROOT', tmp_path)
    client = TestClient(main.create_app(), base_url='https://codemind-gzke.onrender.com')
    assert client.get('/').text == 'CodeMind frontend'
    assert client.head('/').status_code == 200
    # Invalid input reaches API validation, rather than failing the origin check.
    assert client.post('/api/tasks', json={}, headers={'Origin': 'https://codemind-gzke.onrender.com'}).status_code == 422
    for origin in ['https://other.onrender.com', 'https://codemind-gzke.onrender.com.evil.invalid', 'null']:
        assert client.post('/api/tasks', json={}, headers={'Origin': origin}).status_code == 403
    assert client.get('/', headers={'Host': 'other.onrender.com'}).status_code == 400
    assert client.get('/openapi.json', headers={'Host': 'localhost'}).status_code == 200


def test_local_defaults_remain_restricted(monkeypatch):
    monkeypatch.delenv('RENDER_EXTERNAL_HOSTNAME', raising=False)
    client = TestClient(main.create_app())
    assert client.get('/openapi.json').status_code == 200
    assert client.get('/openapi.json', headers={'Host': 'codemind-gzke.onrender.com'}).status_code == 400
    assert client.post('/api/tasks', json={}, headers={'Origin': 'http://localhost:5173'}).status_code == 422
    assert client.post('/api/tasks', json={}, headers={'Origin': 'https://codemind-gzke.onrender.com'}).status_code == 403


@pytest.mark.parametrize('host', ['*', '*.onrender.com', 'https://example.com', 'example.com/path'])
def test_invalid_deployment_hostname_is_rejected(monkeypatch, host):
    monkeypatch.setenv('RENDER_EXTERNAL_HOSTNAME', host)
    with pytest.raises(ValueError, match='must be a hostname'):
        main.create_app()
