FROM python:alpine3.17

LABEL version="1.0" 
LABEL maintainer="Geant LSO Team <@geant.org>"

RUN apk add --no-cache bash curl vim
# RUN pip install --pre --extra-index-url https://artifactory.software.geant.org/artifactory/api/pypi/geant-swd-pypi/simple goat-lso

WORKDIR /opt/lso
COPY . .
RUN pip install -e .

# Generate documentation
RUN ./build-docs.sh
# Generate sample configuration file
RUN ln -s config.json.example config.json

# ENTRYPOINT ["sleep", "inf"]
# ENTRYPOINT ["SETTINGS_FILENAME=./config.json", "python", "-m", "lso.app"]
ENTRYPOINT ["./docker/app-run.sh"]
