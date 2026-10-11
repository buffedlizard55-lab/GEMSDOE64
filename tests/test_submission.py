import zipfile
import numpy as np
import pytest
import rasterio
from gems57 import grid
from gems57.submission_writer import write_submission
from gems57.validate import validate
from gems57.gates import format_report


def test_real_grid_writer_roundtrip_and_rejections(tmp_path):
    # Synthetic serialization fixture ONLY, in pytest scratch, never docs/.
    a = np.zeros(grid.SHAPE, np.float32); a[100, 100] = 1
    fp = np.zeros(grid.SHAPE, bool); fp[50:151, 50:151] = True
    sample = tmp_path / 'sample.tif'
    grid.write_geotiff(sample, a)
    path = tmp_path / 'fixture-not-a-submission.tif'
    receipt = write_submission(path, a, sample, fp, name='TEST ONLY', note='Synthetic serialization fixture')
    assert receipt['validator']['all_checks_passed']
    assert receipt['template_report']['ok']
    assert receipt['approved_for_weekly_slot'] is False
    with rasterio.open(path) as src:
        assert src.dtypes == ('float32',)
        assert src.crs.to_epsg() == 32611
        np.testing.assert_array_equal(src.read(1), a)
    with zipfile.ZipFile(path.with_suffix('.zip')) as z:
        assert z.namelist() == [path.name]
        assert z.read(path.name) == path.read_bytes()
    with pytest.raises(FileExistsError):
        write_submission(path, a, sample, fp, name='x', note='x')
    for bad in (1.01, -9999, np.nan, np.inf):
        a[100, 100] = bad
        with pytest.raises(ValueError):
            write_submission(tmp_path / 'bad.tif', a, sample, fp, name='x', note='x')
        assert not (tmp_path / 'bad.tif').exists()
    a[100, 100] = 0
    with pytest.raises(ValueError, match='preflight'):
        write_submission(tmp_path / 'empty.tif', a, sample, fp, name='x', note='x')
    assert not (tmp_path / 'empty.tif').exists()
    assert not list(tmp_path.glob('.*.tif'))


def test_refuse_shape_or_long_note_before_writing(tmp_path):
    a = np.zeros((3, 3), np.float32)
    with pytest.raises(ValueError, match='140'):
        write_submission(tmp_path/'bad.tif', a, tmp_path/'absent.tif', a == 0,
                         name='x', note='x' * 141)
    with pytest.raises(ValueError, match='matching'):
        write_submission(tmp_path/'bad.tif', a, tmp_path/'absent.tif', np.ones((2, 2)), name='x', note='x')
