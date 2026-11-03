# MySumiller Data Pipeline: X-Wines

Pipeline local para perfilar, limpiar y analizar el catálogo X-Wines de 100.646 vinos y un subconjunto operacional de hasta 100.000 filas de valoraciones. No modifica la aplicación MySumiller, no accede a Supabase y no mezcla las valoraciones de X-Wines con futuras valoraciones propias.

## Datos y alcance

Los CSV completos originales se guardan en `data/raw/` y se excluyen de Git. Los dos ficheros locales fueron comprobados contra los SHA-256 publicados en `INFO_Hashing.txt` antes de copiarlos. El catálogo ocupa 35.843.110 bytes y el CSV de valoraciones 1.123.619.885 bytes. Los hashes verificados son:

- `XWines_Full_100K_wines.csv`: `eac2d812b5eb94264f3c4ee1764ccdacf764cdf1c2599c26e3832ed91a4662cc`
- `XWines_Full_21M_ratings.csv`: `847fb49139b7ebfc92c5745cc34e3efff9febea05e977e4332287afa2ea2ded2`

La fase actual analiza una muestra uniforme reproducible de hasta 100.000 valoraciones. Para seleccionarla, recorre las 21 millones de filas secuencialmente en bloques, pero solo conserva la muestra en memoria; la primera ejecución puede tardar. La muestra queda cacheada y se reutiliza mientras no cambien el CSV, el tamaño solicitado o la semilla. Los resultados de ratings se refieren a esta muestra y no se presentan como agregaciones completas de los 21 millones. El catálogo completo sí se perfila y limpia.

Fuente: X-Wines Dataset 1.0, enero de 2023. Publicación asociada: de Azambuja, R. X., Morais, A. J., & Filipe, V. (2023), “X-Wines: A Wine Dataset for Recommender Systems and Machine Learning”, *Big Data and Cognitive Computing*, 7(1), artículo 20, DOI: https://doi.org/10.3390/bdcc7010020. Verifica las condiciones de licencia y uso comercial antes de integrar estos datos en un producto.

## Entorno

Desde esta carpeta, instala el proyecto y las herramientas de desarrollo:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## Comandos

Ejecuta desde `data-pipeline/`:

```powershell
python -m wine_pipeline.cli profile
python -m wine_pipeline.cli clean
python -m wine_pipeline.cli validate
python -m wine_pipeline.cli analyze
python -m wine_pipeline.cli all
python -m wine_pipeline.cli analyze --show
pytest
jupyter lab
```

Para importar el paquete desde el código fuente sin instalarlo, establece `PYTHONPATH=src`. Los productos Parquet requieren PyArrow, incluido en las dependencias del proyecto.

## Productos

- `reports/data_quality/`: perfil del catálogo completo y del subconjunto de valoraciones, validaciones, errores de parseo y candidatos de posibles duplicados.
- `reports/summary/eda_metrics.json`: estadísticas descriptivas, completitud, distribución de ratings y frecuencias por usuario/vino, con alcance documentado.
- `reports/figures/`: histogramas/diagramas de caja, ratings medios por tipo y país, scatter ABV-rating por vino, heatmap Spearman y pairplot. El notebook los presenta inline; `--show` abre las figuras del CLI en una sesión gráfica.
- `data/processed/xwines_catalog.parquet`: catálogo normalizado con columnas originales y variables derivadas.
- `data/interim/xwines_ratings_sample.parquet`: muestra de ratings con columna `source="X-Wines"`.

Las reglas de limpieza no eliminan vinos ni ratings extremos. Los límites IQR son señales para investigar, no reglas de borrado. Las claves de entidad no se escalan. Los candidatos a duplicado son orientativos y nunca se fusionan automáticamente.

## Columnas y análisis

El catálogo procesado conserva los 17 campos originales, incluidos los IDs, Website y Vintages. La vista analítica usa `ABV` para revisar valores extremos y `Type`, `Country`, `Body` y `Acidity` para comparar completitud y categorías. Los análisis de ratings usan `Rating`, `UserID`, `WineID`, `Vintage` y `Date`; RatingID se conserva para controles de unicidad. El join con el catálogo exige `WineID` único y cardinalidad muchos-a-uno. Las medias se muestran junto con el tamaño muestral y no se interpretan como causalidad ni como calidad intrínseca.

## Memoria

Ejecuta primero `python -m wine_pipeline.cli all` y después abre `memoria.ipynb` con JupyterLab. El notebook consume informes y figuras generados; no vuelve a recorrer el CSV de 21 millones. Los análisis de ratings se limitan a la muestra uniforme de hasta 100.000 filas. Las asociaciones son descriptivas y no controlan la dependencia entre ratings de un mismo usuario.

## Modelo futuro y trazabilidad

Las entidades conceptuales futuras pueden incluir `wines`, `ratings` con `source`, `wine_sources`, `wine_aliases`, `wineries` y `regions`. `UserID` se considera un identificador anonimizado. No se crean tablas de producción ni se atribuyen los ratings externos a usuarios MySumiller. Para futuras versiones de datos puede evaluarse DVC, sin necesidad de añadirlo ahora.