# Diccionario de datos

## Catálogo X-Wines

| Columna | Significado y tratamiento |
|---|---|
| `WineID` | ID de origen estable; no se modifica ni se trata como magnitud. |
| `WineName` | Nombre de presentación; se recortan y compactan espacios, preservando mayúsculas y acentos. |
| `Type`, `Elaborate`, `Body`, `Acidity` | Atributos categóricos; se preservan sus valores y nulos. |
| `Grapes`, `Harmonize`, `Vintages` | Listas codificadas en texto; se parsean con `ast.literal_eval`, nunca con `eval`. Los errores se registran. `N.V.` se conserva como marcador no numérico. |
| `ABV` | Graduación alcohólica; se convierte a numérico cuando es posible. Los extremos se señalan mediante IQR y no se eliminan. |
| `Code`, `Country` | Código de país y país de procedencia, conservados. |
| `RegionID`, `RegionName` | Identificador y etiqueta de región, conservados. |
| `WineryID`, `WineryName` | Identificador y etiqueta de bodega, conservados. |
| `Website` | Metadato de origen; solo se normalizan espacios externos. |

## Valoraciones X-Wines

| Columna | Significado y tratamiento |
|---|---|
| `RatingID` | ID externo usado para revisar unicidad. |
| `UserID` | ID anonimizado de usuario; no es dato personal ni variable continua. |
| `WineID` | Referencia al catálogo; se mide la cobertura referencial. |
| `Vintage` | Añada numérica cuando se puede convertir; valores no interpretables permanecen ausentes en la vista tipada y se cuantifican. |
| `Rating` | Puntuación numérica; se valida en rango 1–5 y compatibilidad con incrementos de 0,5. |
| `Date` | Fecha con formato esperado `%Y-%m-%d %H:%M:%S`; errores se convierten en nulos tipados y se cuentan. |

Los ratings procesados conservan la procedencia `X-Wines` por el nombre del producto y nunca se mezclan con ratings propios de MySumiller.