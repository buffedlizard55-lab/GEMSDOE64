import importlib.util
from pathlib import Path


def test_no_broken_links_or_unsafe_downloads():
    spec = importlib.util.spec_from_file_location('check_site', Path('scripts/check_site.py'))
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    result = mod.check()
    assert result['ok'], result['problems']
    assert result['approved_tiff_links'] == 0


def test_site_data_are_not_gitignored():
    import subprocess
    result = subprocess.run(['git', 'check-ignore', '--no-index', 'docs/data/run_card.json'],
                            capture_output=True, text=True)
    assert result.returncode == 1, result.stdout + result.stderr
