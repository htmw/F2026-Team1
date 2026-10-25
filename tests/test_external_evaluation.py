"""Check external labels without collecting model predictions."""

import csv
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import evaluate_external as evaluator


def test_dataset_paths_labels_and_counts(tmp_path, monkeypatch):
    monkeypatch.setitem(evaluator.DATASETS, 'ORIGA', ('origa_labels.csv', 2, {'glaucoma': 1}))
    directory = tmp_path / 'labels/external'
    directory.mkdir(parents=True)
    path = directory / 'origa_labels.csv'
    records = [dict(filename=f'{i}.jpg', path=f'External/ORIGA/nested/{i}.jpg',
                    split='test', glaucoma=str(i)) for i in range(2)]
    def save():
        with path.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)
    save()
    assert evaluator.read_dataset(tmp_path, 'ORIGA')[0]['preprocessed'] == 'Preprocessed/ORIGA/nested/0.jpg'
    records[0]['path'] = '../outside/0.jpg'
    save()
    with pytest.raises(ValueError, match='leaves its dataset'):
        evaluator.read_dataset(tmp_path, 'ORIGA')
    records[0]['path'] = 'External/ORIGA/nested/0.jpg'
    records[0]['glaucoma'] = '1'
    save()
    with pytest.raises(ValueError, match='disease counts'):
        evaluator.read_dataset(tmp_path, 'ORIGA')


def test_run_option_is_unavailable(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['evaluate_external.py', '--run'])
    monkeypatch.setattr(evaluator, 'preflight', lambda: pytest.fail('Unexpected preflight'))
    with pytest.raises(SystemExit) as error:
        evaluator.main()
    assert error.value.code == 2
