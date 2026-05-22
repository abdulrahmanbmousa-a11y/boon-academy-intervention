param([Parameter(Mandatory=$true)][string]$Target)
switch ($Target) {
    "install" {
        pip install -r requirements.txt -r requirements-dev.txt
    }
    "demo" {
        python -m src.generate_data
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        python main.py
    }
    "test" {
        pytest tests/ -v
    }
    "clean" {
        Remove-Item -Recurse -Force outputs, __pycache__, src/__pycache__, .pytest_cache, .coverage -ErrorAction SilentlyContinue
    }
    default {
        Write-Error "Unknown target '$Target'. Valid: install, demo, test, clean"
        exit 1
    }
}
