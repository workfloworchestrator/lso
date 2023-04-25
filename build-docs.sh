python docs/dump-openapi-spec.py

sphinx-apidoc lso lso/app.py -o docs/source -d 2 -f
vale --config=docs/vale/.vale.ini docs/source/*.rst lso/*.py
sphinx-build -b html docs/source docs/build
