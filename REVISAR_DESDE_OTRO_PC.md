# Revisar el software desde otro PC

Este repositorio trabaja con **una sola rama: `main`**. No hay ramas de
desarrollo, ni `master`, ni ramas por funcionalidad. Todo cambio que exista
esta en `main`, y lo que no esta en `main` no existe.

La razon es practica: el software corre en la clinica y tiene que haber un
unico sitio donde mirar para saber que se esta ejecutando. Con varias ramas
vivas, "la version del laboratorio" deja de ser una pregunta con respuesta.

## Traerse el proyecto

```
git clone https://github.com/AndresDiaz2012/ANgesLAB.git
cd ANgesLAB
```

## Ver que hay y desde cuando

```
cat VERSION                     # la version publicada
git log --oneline -20           # los ultimos cambios, uno por linea
git tag -l                      # las versiones etiquetadas
```

Cada version lleva su etiqueta. Para ver exactamente que cambio entre dos:

```
git log --oneline v2.5.7..v2.6.0
git diff --stat v2.5.7 v2.6.0
```

## Ver un cambio concreto

```
git show <hash>                 # el cambio entero, con su explicacion
git log -p -- modulos/tarifas.py   # la historia de un archivo
```

Los mensajes de commit explican **por que** se hizo cada cambio, no solo
que se toco. Leerlos es la via rapida para entender una decision sin tener
que reconstruirla desde el codigo.

## Comprobar que todo sigue en pie

```
python -m pytest tests/ -q
```

## Traerse las actualizaciones

```
git pull
```

Como solo hay una rama, `git pull` siempre trae lo ultimo y nunca hay que
elegir de donde. Si `git status` dice algo distinto de `nothing to commit`
y `up to date with origin/main`, hay algo sin subir o sin bajar.

## Que NO viaja en el repositorio

Y no es un olvido, es deliberado:

| Que | Donde vive | Por que |
|---|---|---|
| `ANgesLAB.accdb` | solo en la instalacion | datos clinicos de pacientes |
| `logos/`, `firmas/` | solo en la instalacion | imagenes del laboratorio |
| `config_whatsapp.json` | solo en la instalacion | configuracion de esa maquina |
| `backups/` | solo en la instalacion | respaldos locales |

Quien clone el repositorio obtiene el **programa**, no los datos ni la
identidad del laboratorio. Para levantar una instalacion nueva hay que
crear la base con `crear_plantilla_bd.py` y cargar los datos del
laboratorio desde la propia aplicacion.

## Como se publica un cambio

1. Trabajar sobre `main`.
2. `python -m pytest tests/ -q` antes de subir.
3. Commit con un mensaje que explique el porque.
4. `git push`.
5. Si el cambio merece version: actualizar `VERSION`, commit, y etiquetar
   con `git tag -a vX.Y.Z -m "..."` y `git push origin vX.Y.Z`.
