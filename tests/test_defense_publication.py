"""Tiny publication-adapter checks; no formal media or D5 source-lock changes."""
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('publication_adapter',
    Path(__file__).parents[1] / 'scripts/defense_mvp/publish_d5_docs.py')
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


def test_path_whitespace_normalization_preserves_semantics():
    original = b'<svg xmlns="http://www.w3.org/2000/svg"><path d="M 0 0 \nL 1 2 \n"/></svg>\n'
    result = adapter.normalize_svg(original)
    assert b' \n' not in result
    assert adapter.svg_semantics(result) == adapter.svg_semantics(original)
    assert adapter.normalize_svg(result) == result


def test_textual_whitespace_change_is_rejected():
    with pytest.raises(ValueError, match='semantics'):
        adapter.normalize_svg(b'<svg><text>meaningful \ntext</text></svg>\n')


def fake_files(*args):
    return {'DEFENSE_REPORT.md': b'report\n',
            'd5_generated/figures/test.svg': b'<svg xmlns="http://www.w3.org/2000/svg"><path d="M 0 0 \n"/></svg>\n',
            'd5_generated/public-export.json': b'{}'}


def test_edited_document_rejected_before_any_writes(tmp_path, monkeypatch):
    monkeypatch.setattr(adapter, 'public_files', fake_files)
    (tmp_path / 'DEFENSE_REPORT.md').write_bytes(b'user edit')
    with pytest.raises(ValueError, match='edited document'):
        adapter.publish(tmp_path, tmp_path, tmp_path)
    assert (tmp_path / 'DEFENSE_REPORT.md').read_bytes() == b'user edit'
    assert not (tmp_path / 'd5_generated').exists()


def test_publish_verify_tamper_and_unknown_file(tmp_path, monkeypatch):
    monkeypatch.setattr(adapter, 'public_files', fake_files)
    adapter.publish(tmp_path, tmp_path, tmp_path)
    adapter.verify(tmp_path, tmp_path, tmp_path)
    svg = tmp_path / 'd5_generated/figures/test.svg'
    original = svg.read_bytes()
    svg.write_bytes(original.replace(b'M 0 0', b'M 1 0'))
    with pytest.raises(ValueError, match='drift'):
        adapter.verify(tmp_path, tmp_path, tmp_path)
    svg.write_bytes(original)
    (tmp_path / 'd5_generated/unknown.txt').write_text('unregistered')
    with pytest.raises(ValueError, match='unknown'):
        adapter.verify(tmp_path, tmp_path, tmp_path)
