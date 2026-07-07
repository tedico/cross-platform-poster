import pytest

from src.assets import download_assets, AssetError


def _resp(mocker, status_code=200, chunks=None):
    resp = mocker.MagicMock(status_code=status_code)
    if chunks is not None:
        resp.iter_content.return_value = chunks
    resp.__enter__.return_value = resp
    return resp


def test_downloads_to_tmp_with_filename(mocker, tmp_path):
    resp = _resp(mocker, chunks=[b"vid"])
    mocker.patch("src.assets.requests.get", return_value=resp)
    paths = download_assets(["https://a.example/store/hua-luogeng.mp4"],
                            tmp_path, token="t")
    assert paths[0].name == "hua-luogeng.mp4"
    assert paths[0].read_bytes() == b"vid"


def test_sends_token_header(mocker, tmp_path):
    resp = _resp(mocker, chunks=[b"x"])
    get = mocker.patch("src.assets.requests.get", return_value=resp)
    download_assets(["https://a/x.mp4"], tmp_path, token="sekret")
    assert get.call_args.kwargs["headers"] == {"X-Token": "sekret"}


def test_http_error_raises(mocker, tmp_path):
    resp = _resp(mocker, status_code=404)
    mocker.patch("src.assets.requests.get", return_value=resp)
    with pytest.raises(AssetError, match="404"):
        download_assets(["https://a/x.mp4"], tmp_path, token=None)


def test_duplicate_basenames_raise(mocker, tmp_path):
    get = mocker.patch("src.assets.requests.get")
    with pytest.raises(AssetError, match="duplicate"):
        download_assets(["https://a/one/img.png", "https://a/two/img.png"],
                        tmp_path, token=None)
    get.assert_not_called()


def test_empty_body_raises(mocker, tmp_path):
    resp = _resp(mocker, chunks=[])
    mocker.patch("src.assets.requests.get", return_value=resp)
    with pytest.raises(AssetError, match="empty"):
        download_assets(["https://a/x.mp4"], tmp_path, token=None)
