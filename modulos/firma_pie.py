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


# Cuanto de la firma cae POR DEBAJO de la linea guia, en tanto por uno de
# su altura.
#
# Una firma de verdad no se posa encima de la raya: se arranca sobre ella y
# los trazos largos bajan y cruzan lo que haya escrito debajo. Dejarla
# flotando limpia por encima delata que es una imagen pegada. Los trazos son
# finos, asi que cruzan el nombre sin taparlo.
SOLAPE_LINEA = 0.40

# Pero con tope, porque el 40% de una firma alta es mucho en pulgadas: una
# firma de 1,6 pulgadas caeria 0,64, y como la raya esta a 0,64 del borde,
# la firma llegaria hasta el canto de la hoja tapando el numero de orden y
# la fecha.
#
# Con 0,30 el trazo cruza el nombre y el titulo y alcanza el numero de
# registro, que son las tres lineas del bloque. Por debajo de ahi ya no hay
# datos de la firma sino el pie de pagina del informe, y ese no se toca.
CAIDA_MAXIMA = 0.30 * 72.0  # puntos


def encajar(ruta, ancho_max, alto_max):
    """
    El tamano con que se dibuja la firma dentro de su hueco, sin deformarla.

    Se calcula aqui en vez de dejarselo a preserveAspectRatio porque hace
    falta saber el tamano REAL para colocarla: el solape se mide sobre lo
    que la firma ocupa, no sobre el hueco. Una firma apaisada apenas llena
    un tercio de la altura del hueco, y usar la del hueco la hundiria entera
    por debajo de la linea.

    Devuelve (ancho, alto). Si no se puede leer la imagen, devuelve el hueco
    entero, que es lo que se hacia antes.
    """
    try:
        from reportlab.lib.utils import ImageReader
        w, h = ImageReader(ruta).getSize()
    except Exception:
        return ancho_max, alto_max
    if not w or not h:
        return ancho_max, alto_max
    escala = min(ancho_max / float(w), alto_max / float(h))
    return w * escala, h * escala


def caida(alto, caida_maxima=None):
    """Cuanto baja la firma por debajo de la raya, en puntos."""
    tope = CAIDA_MAXIMA if caida_maxima is None else caida_maxima
    return min(alto * SOLAPE_LINEA, tope)


def posicion_firma(ruta, ancho_max, alto_max, y_linea, caida_maxima=None):
    """
    Donde y de que tamano se dibuja la firma para que monte sobre la linea.

    Devuelve (ancho, alto, y), con y medido desde el borde inferior de la
    pagina hasta la base de la imagen.
    """
    ancho, alto = encajar(ruta, ancho_max, alto_max)
    return ancho, alto, y_linea - caida(alto, caida_maxima)


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
