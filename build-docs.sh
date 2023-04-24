python docs/dump-openapi-spec.py

sphinx-apidoc lso lso/app.py -o docs/source -d 2 -f
sphinx-build -b html docs/source docs/build
