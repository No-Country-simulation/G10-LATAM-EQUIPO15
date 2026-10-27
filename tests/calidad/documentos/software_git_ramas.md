# Flujo de trabajo con ramas en Git

## Para qué sirven las ramas
Una rama es una línea de desarrollo independiente. Permite trabajar en una funcionalidad o corrección sin afectar la rama principal, que suele llamarse `main`. Cuando el trabajo está listo, la rama se integra de nuevo.

## Crear una rama y cambiar a ella
El comando `git switch -c` crea una rama nueva y cambia a ella en un solo paso:

```bash
git switch -c funcionalidad/login
```

Para volver a la rama principal se usa `git switch main`.

## Integrar cambios con merge
`git merge` combina el historial de otra rama con la rama actual. Si ambas ramas modificaron las mismas líneas de un archivo, Git detiene la integración y marca un conflicto que debe resolverse a mano antes de confirmar.

```bash
git switch main
git merge funcionalidad/login
```

## Rebase
`git rebase` reaplica los commits de una rama sobre otra base, lo que produce un historial lineal. No se recomienda hacer rebase de commits que ya fueron publicados y que otras personas usan, porque reescribe su historia.

## Pull requests
En plataformas como GitHub, una pull request propone integrar una rama y permite que otras personas revisen el código antes de aceptarlo. Es habitual exigir que las pruebas automáticas pasen antes de integrar.
