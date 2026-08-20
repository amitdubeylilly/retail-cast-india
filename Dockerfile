# Validates that all Python packages resolve exclusively from JFrog Artifactory
# (elilillyco.jfrog.io), never from public PyPI. Matches runtime_version in agent_config.json.
FROM python:3.11-slim

WORKDIR /app

# pip.conf is supplied only as a BuildKit secret (never written to an image layer).
# /etc/pip.conf is pip's default global config location, so no flags are needed —
# whatever index-url/trusted-host it sets (Artifactory only, no PyPI fallback) applies.
COPY requirements.txt .
RUN --mount=type=secret,id=pipconf,target=/etc/pip.conf,required=true \
    pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY data/ data/
COPY validate_format.py .

CMD ["python", "src/forecast.py", "--data", "data", "--out", "submission.csv"]
