# Instrucciones para ejecutar tests y verificar cobertura

Estos pasos asumen Windows + PowerShell y un entorno virtual activado en la raíz del proyecto.

1. Ejecutar todos los tests unitarios

```powershell
pytest -q tests/unit
```

2. Ejecutar tests por marca o archivo

- Ejecutar solo pruebas marcadas como `cache`:

```powershell
pytest -q -m cache
```

- Ejecutar un archivo específico:

```powershell
pytest -q tests/unit/test_cache_service.py
```

3. Ejecutar la suite completa con reporte de cobertura (terminal) esto para los archivos de pruebas unitarias

```powershell
pytest --cov=app.services --cov=app.schemas --cov=app.models --cov-report=term-missing tests/unit
```

4. Generar reporte de cobertura HTML (más legible)

```powershell
pytest --cov=app --cov-report=html
# luego abrir htmlcov/index.html en el navegador
```

5. Ejecutar solo tests de integración

```powershell
pytest -q -m integration
```

Notas y recomendaciones


Si quieres, ejecuto los comandos de pruebas ahora y te paso la salida. (Necesito confirmación para ejecutarlos.)
