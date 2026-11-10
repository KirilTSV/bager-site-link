"""Run API tests in isolated temporary SQLite databases; never production."""
import os,sys,subprocess,tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
tests=['tests/test_pilot_flow.py','tests/test_shift_status.py','tests/test_gps_integrity.py','tests/test_operations.py']
for test in tests:
    with tempfile.TemporaryDirectory(prefix='bager-api-test-') as temp:
        env={**os.environ,'BAGER_TEST_DB':str(Path(temp)/'test.sqlite3'),'DATABASE_URL':'sqlite:///'+str(Path(temp)/'test.sqlite3'),'BAGER_ADMIN_PASSWORD':'test-only-password-2026'}
        result=subprocess.run([sys.executable,'-m','pytest','-q',test],cwd=root,env=env)
        if result.returncode:sys.exit(result.returncode)
print('All isolated API tests passed.')
