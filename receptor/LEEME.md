# ANgesLAB Receptor

El programa que **imprime** en la sede que toma las muestras.

```
Sede A (procesa)                      Sede B (toma muestras)
----------------                      ----------------------
valida el resultado
pulsa «Enviar a sede»
    |                                  ESTE programa, vigilando
    v                                         |
PDF a la carpeta  ---- Drive/OneDrive ---->  lo ve llegar
                                              |
                                          imprime  ->  papel
```

Esta sede **no tiene ANgesLAB ni base de datos**. Este programa solo sabe
mirar una carpeta e imprimir: no puede consultar ni modificar ningun
resultado. Esa limitacion es la garantia de que el informe no se altera de
camino.

## Instalar en la sede B

1. Copiar a ese equipo la carpeta `receptor/` **y** la carpeta `modulos/`,
   manteniendo la misma estructura:

   ```
   ANgesLAB_Receptor/
       receptor/ANgesLAB_Receptor.pyw
       modulos/impresoras.py
       modulos/logging_config.py
   ```

   La base de datos NO se copia. No hace falta y no debe estar ahi.

2. Instalar Python 3.12 y las dos librerias que usa el motor de impresion:

   ```
   pip install pymupdf pywin32
   ```

3. Abrir `receptor/ANgesLAB_Receptor.pyw` con doble clic.

4. En la ventana: elegir la **carpeta** sincronizada que llega de la sede
   central, la **impresora**, y pulsar «Empezar a vigilar».

Marcando «Empezar a vigilar al abrir el programa» queda listo para dejarlo
en el arranque de Windows y olvidarse.

## Que hace con cada archivo

1. **Espera a que deje de crecer.** El emisor escribe con nombre temporal y
   renombra al terminar, pero una carpeta sincronizada puede entregar el
   archivo mientras todavia baja. Una hoja en blanco no se nota hasta que el
   paciente reclama.
2. **Lo imprime.**
3. **Lo mueve** a `impresos/AAAA-MM/`. Nunca se borra nada: si una hoja sale
   mal, el PDF sigue ahi para repetirla.
4. Si la impresion **falla**, va a `errores/` y queda anotado en
   `receptor.log` con el motivo. No se reintenta en bucle: un atasco de papel
   repetido cien veces llena la cola y no arregla nada.

## Si algo no sale

| Lo que se ve | Que pasa |
|---|---|
| «La carpeta no esta disponible» | Drive u OneDrive aun no han montado la unidad, o no hay red. Sigue esperando solo. |
| Archivos en `errores/` | La impresora rechazo el documento. El motivo esta en `receptor.log`. Se repiten arrastrandolos a la carpeta vigilada. |
| No aparece ninguna impresora | Falta `pywin32`, o el equipo no tiene impresoras instaladas. |
| «No se pudo cargar el motor de impresion» | Falta la carpeta `modulos/` al lado, o falta `pymupdf`. |

`receptor.log` y la carpeta `impresos/` son lo unico con lo que la sede B
puede responder a «este resultado nunca llego». No se borran.
