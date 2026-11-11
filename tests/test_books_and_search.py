"""Tests for homepage, four generations, advanced search, reader, and download permissions."""


def test_homepage_and_generation_sections(client):
    res = client.get('/')
    assert res.status_code == 200
    assert b'Knowledge Belongs to Everyone.' in res.data
    assert b'Explore Library' in res.data
    assert b'Donate a Book' in res.data

    for path in ('/children/', '/youth/', '/adults/', '/seniors/', '/about', '/contact'):
        r = client.get(path)
        assert r.status_code == 200


def test_search_and_filters(client):
    res = client.get('/books/search?q=Aesop')
    assert res.status_code == 200
    assert b"Aesop&#39;s Fables" in res.data or b"Aesop's Fables" in res.data

    res = client.get('/books/search?q=9781491939369&sort=alphabetical')
    assert res.status_code == 200
    assert b'Think Python' in res.data

    res = client.get('/api/search/suggestions?q=Python')
    assert res.status_code == 200
    assert b'Think Python' in res.data


def test_reader_and_download_permission_enforcement(client):
    # Book 1 is downloadable & readable
    r1 = client.get('/books/1/read')
    assert r1.status_code == 200

    # Book 2 has is_downloadable=False -> should NOT serve file, redirects with warning
    r2 = client.get('/books/2/download', follow_redirects=True)
    assert r2.status_code == 200
    assert b'Downloading is not permitted' in r2.data

