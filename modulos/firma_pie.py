# -*- coding: utf-8 -*-
"""
================================================================================
BLOQUE DE FIRMA DEL BIOANALISTA
================================================================================
Lo que va escrito debajo de la linea de firma, al pie de un informe.

Existe porque ese bloque estaba copiado en tres sitios -el informe de
resultados, el envio por correo y el reporte de control- y los tres tenian
que decir exactamente lo mismo. Una firma que en un papel dice un numero de
registro y en otro dice otro no vale nada, y tres copias del mismo codigo
acaban separandose siempre.

El formato es el que el laboratorio usa en sus informes:

        ______________________
         Filadelfo G. Diaz B.
          LCDO. BIOANALISIS
          N 17.421-12.120

Es decir: nombre, titulo profesional y numero de registro. Nada mas.

El titulo sale de Bioanalistas.TituloProfesional. Si ese campo esta vacio
-una instalacion que venga de antes, o un bioanalista recien dado de alta-
se recurre al area, que es lo que se hacia hasta ahora, y asi ningun
informe se queda sin pie mientras se completan los datos.

La cedula no se imprime: no aparece en el formato del laboratorio, y quien
verifica a un bioanalista lo hace por su numero de registro. Sigue guardada
en la ficha para uso interno.

Copyright 2024-2026 ANgesLAB Solutions
================================================================================
"""

# Fuentes de cada linea, para que los tres sitios pinten igual. El tamano es
# relativo: cada informe tiene el suyo segun el tamano de papel.
FUENTE_NOMBRE = 'Helvetica-Bold'
FUENTE_TITULO = 'Helvetica'
FUENTE_REGISTRO = 'Helvetica'

# Etiqueta del numero de registro. Va delante del numero tal como esta
# guardado, sin tocarlo: el formato del numero (con puntos, con guion, con
# dos registros seguidos) es cosa del colegio profesional, no del programa.
ETIQUETA_REGISTRO = 'N° '


def _texto(valor):
    return str(valor).strip() if valor is not None else ''


def titulo_de(bio):
    """
    El titulo que se imprime bajo el nombre.

    Lo que el propio bioanalista tenga cargado; si no, su area; si tampoco,
    'Bioanalista' a secas, que siempre es cierto.
    """
    titulo = _texto(bio.get('TituloProfesional'))
    if titulo:
        return titulo
    area = _texto(bio.get('NombreArea'))
    if area and area.lower() != 'general':
        return 'Bioanalista - ' + area
    return 'Bioanalista'


def lineas_firma(bio):
    """
    Las lineas del bloque, de arriba abajo.

    Devuelve una lista de (texto, fuente, clase), donde clase dice de que
    tamano es la linea para el informe que la pinta:

        'nombre'    la linea principal
        'detalle'   las de debajo

    Se devuelven en vez de dibujarse porque cada informe tiene su canvas,
    sus tamanos de fuente y su interlineado; lo unico que tienen que
    compartir es QUE dicen y en que orden.
    """
    lineas = [(_texto(bio.get('NombreCompleto')), FUENTE_NOMBRE, 'nombre'),
              (titulo_de(bio), FUENTE_TITULO, 'detalle')]

    registro = _texto(bio.get('NumeroRegistro'))
    if registro:
        lineas.append((ETIQUETA_REGISTRO + registro, FUENTE_REGISTRO, 'detalle'))

    # Una linea vacia dejaria un hueco en el bloque y descuadraria el resto
    return [l for l in lineas if l[0]]


def asegurar_columna_titulo(db):
    """
    Crea Bioanalistas.TituloProfesional si falta.

    Se queda en NULL, que significa 'usa el area', asi que una instalacion
    que venga de antes sigue imprimiendo lo mismo hasta que alguien cargue
    el titulo.
    """
    try:
        db.query_one("SELECT TOP 1 TituloProfesional FROM Bioanalistas")
        return True
    except Exception:
        pass
    try:
        db.execute("ALTER TABLE Bioanalistas ADD COLUMN TituloProfesional TEXT(100)")
        return True
    except Exception:
        return False
