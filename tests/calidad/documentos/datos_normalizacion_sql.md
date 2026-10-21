# Normalización de bases de datos relacionales

## Objetivo
La normalización organiza las tablas para evitar datos repetidos y anomalías al insertar, actualizar o eliminar registros. Cada hecho debe guardarse en un solo lugar.

## Primera forma normal (1FN)
Una tabla está en 1FN cuando cada columna contiene valores atómicos, es decir, un solo valor por celda, y no hay grupos repetidos. Guardar varios teléfonos separados por comas en una misma columna viola la 1FN.

## Segunda forma normal (2FN)
Una tabla está en 2FN si está en 1FN y cada columna que no forma parte de la clave depende de la clave primaria completa. El problema aparece con claves compuestas: si una columna depende solo de una parte de la clave, debe moverse a otra tabla.

## Tercera forma normal (3FN)
Una tabla está en 3FN si está en 2FN y ninguna columna no clave depende de otra columna no clave. Por ejemplo, si una tabla de empleados guarda el código de departamento y también el nombre del departamento, el nombre depende del código y no del empleado.

## Resumen de las formas normales

| Forma normal | Requisito principal |
|---|---|
| 1FN | Valores atómicos, sin grupos repetidos |
| 2FN | Sin dependencias parciales de la clave |
| 3FN | Sin dependencias transitivas |

## Desnormalización
En sistemas de análisis a veces se desnormaliza a propósito: se duplican datos para evitar uniones costosas en las consultas. Es una decisión de rendimiento que acepta el riesgo de inconsistencias.
