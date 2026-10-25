"""Synthetic checks only. No external model predictions are collected."""

import csv
import json
from pathlib import Path
import sys

import numpy as np
import pytest
import torch
from PIL import Image

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


def test_inference_batches_and_shared_head_order(tmp_path, monkeypatch):
    monkeypatch.setattr(evaluator, 'PROJECT_ROOT', tmp_path)
    Image.new('RGB', (512, 512)).save(tmp_path / 'synthetic.png')
    rows = [{'preprocessed': 'synthetic.png'}] * 9
    class Stub(torch.nn.Module):
        def forward(self, x):
            assert not torch.is_grad_enabled()
            return torch.ones(len(x), 1), torch.full((len(x), 1), 2.)
    assert evaluator.infer(Stub(), rows, True) == [[1.] * 9, [2.] * 9]


def test_run_requires_review_before_any_preflight(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['evaluate_external.py', '--run'])
    monkeypatch.setattr(evaluator, 'preflight', lambda: pytest.fail('Must not inspect or score inputs'))
    with pytest.raises(SystemExit) as error:
        evaluator.main()
    assert error.value.code == 2


def test_existing_campaign_cannot_be_overwritten(tmp_path):
    with pytest.raises(FileExistsError):
        evaluator.evaluate(tmp_path, {}, {}, {}, 'review')


@pytest.fixture
def synthetic_campaign(monkeypatch):
    """Replace model inference with known outputs for a tiny synthetic campaign."""
    datasets = {
        name: [dict(path=f'External/{name}/{i}.png', **{d: i for d in entry[2]})
               for i in range(2)] for name, entry in evaluator.DATASETS.items()
    }
    settings = {'runs': [dict(model_kind=kind, disease=disease, seed=seed,
                             checkpoint='synthetic.pt', scale=1., offset=0.,
                             threshold=0.5, uncertain_margin=0.05)
                         for kind in ('single', 'shared')
                         for disease in ('cataract', 'glaucoma') for seed in (42, 43, 44)]}
    monkeypatch.setattr(evaluator, 'load_model', lambda seed: (object(), {}))
    monkeypatch.setattr(evaluator, 'load_cataract_model', lambda seed: object())
    monkeypatch.setattr(evaluator, 'load_glaucoma_model', lambda path, seed: object())
    monkeypatch.setattr(evaluator, 'infer', lambda model, rows, shared:
                        [[-2., 2.], [-2., 2.]] if shared else [[-2., 2.]])
    return settings, datasets


def test_synthetic_predictions_saved_with_correct_labels(tmp_path, synthetic_campaign):
    settings, datasets = synthetic_campaign
    output = tmp_path / 'campaign'
    evaluator.evaluate(output, settings, datasets, {}, 'synthetic-test-only')
    with (output / 'predictions.csv').open() as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 60
    assert all(r['dataset'] == 'retina_dataset_2016' for r in rows if r['disease'] == 'cataract')
    assert all(r['decision'] == ('Refer' if r['label'] == '1' else 'No concern') for r in rows)
    manifest = json.loads((output / 'run_manifest.json').read_text())
    assert manifest['status'] == 'predictions_saved'
    assert manifest['predictions_sha256'] == evaluator.file_sha256(output / 'predictions.csv')


def test_failed_inference_retains_failure_record(tmp_path, synthetic_campaign, monkeypatch):
    settings, datasets = synthetic_campaign
    def fail(*args):
        raise ValueError('Synthetic failure')
    monkeypatch.setattr(evaluator, 'infer', fail)
    output = tmp_path / 'failed'
    with pytest.raises(ValueError, match='Synthetic failure'):
        evaluator.evaluate(output, settings, datasets, {}, 'synthetic-test-only')
    record = json.loads((output / 'run_manifest.json').read_text())
    assert record['status'] == 'failed'
    assert not (output / 'predictions.csv').exists()
