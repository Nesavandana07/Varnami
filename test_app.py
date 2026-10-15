import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import app

client = app.app.test_client()

# Test index
r = client.get('/')
assert r.status_code == 200, f'GET / failed: {r.status_code}'

# Test ragas
r = client.get('/api/ragas')
assert r.status_code == 200
ragas = r.get_json()
assert len(ragas) >= 16

# Test composer with lyrics
r = client.post('/api/compose', json={
    'a': 'Hamsadhwani',
    'b': 'Ahiri',
    'length': 12,
    'blend': 0.5,
    'seed': 1,
    'lyrics': 'Va-tha-pi Ga-na-pa-thim Bha-je-ham'
})
assert r.status_code == 200
comp = r.get_json()
assert 'lyrics' in comp and 'dual_notation' in comp['lyrics']

print("ALL_TESTS_PASSED_SUCCESSFULLY")
