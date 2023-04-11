import json
import os

from fastapi.testclient import TestClient
import larp

config_filename = os.path.join(
    os.path.dirname(__file__),
    '..', 'config-example.json')

output_filename = os.path.join(
    os.path.dirname(__file__),
    'source', '_static', 'openapi.json')

os.environ['SETTINGS_FILENAME'] = config_filename
app = larp.create_app()
client = TestClient(app)
rsp = client.get('/openapi.json')
openapi_doc = json.dumps(rsp.json(), indent=2)

with open(output_filename, 'w') as f:
    f.write(openapi_doc)

print(f'wrote {output_filename}')
