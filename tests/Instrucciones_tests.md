# Instrucciones para ejecutar tests

Estos pasos asumen Windows + PowerShell y un entorno virtual activado.

## 1. Ejecutar todos los tests (unit + integration)

```powershell
pytest tests/unit tests/integration -q
```

## 2. Ejecutar solo unit O solo integration

```powershell
# Solo unitarios
pytest tests/unit -q

# Solo integración
pytest tests/integration -q
```

## 3. Coverage unitarios para el 90% (services, models, schemas)

```powershell
pytest --cov=app.services --cov=app.schemas --cov=app.models --cov-report=term-missing tests/unit
```

## 4. Ejecutar integration y mostrar coverage

```powershell
pytest --cov=app --cov-report=term tests/integration -q

pytest --cov=app --cov-report=term tests/integration\test_mongodb.py -v

```

## 5. Coverage en HTML (unit e integration)

```powershell
# Unit
pytest --cov=app.services --cov=app.schemas --cov=app.models --cov-report=html tests/unit
# Abre: htmlcov/index.html

# Integration
pytest --cov=app --cov-report=html tests/integration
# Abre: htmlcov/index.html
```

## 6. Coverage para todo 

```
python -m pytest --cov=app --cov-report=term tests/unit tests/integration -q

python -m pytest --cov=app --cov-report=term --cov-report=html tests/unit tests/integration -q #En html
```
