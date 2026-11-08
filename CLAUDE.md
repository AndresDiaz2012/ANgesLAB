# Reglas de trabajo en ANgesLAB

- **Todo cambio termina en GitHub.** Ningun trabajo se da por hecho mientras
  solo exista en una copia local o en la PC de la clinica: se hace commit en
  `main` y se sube (`git push origin main`), y despues se actualiza la carpeta
  de la clinica con `git pull`. Lo pidio el dueño del proyecto el 08/11/2026.
- Una sola rama, `main` (ver `REVISAR_DESDE_OTRO_PC.md`).
- Los mensajes de commit explican el porque, en español y sin tildes.
- Antes de subir: `python -m pytest tests/ -q`. En Linux fallan 18 pruebas que
  dependen de Windows (`test_receptor.py`, `test_formato_pdf.py`); cualquier
  otra falla es real.
- Cada fase del ERP se publica con `VERSION` actualizado y su etiqueta
  `vX.Y.Z`. Si el entorno no deja subir etiquetas, se avisa para subirlas
  desde Windows.
- Situacion fiscal del laboratorio (la dio el dueño el 08/11/2026): es
  contribuyente ORDINARIO, NO es agente de retencion (ni de IVA ni de ISLR)
  y no percibe IGTF. No retiene a sus proveedores; solo recibe las
  retenciones que le hacen sus clientes agentes. Facturacion digital con
  The Factory HKA.
- El diseño del modulo administrativo y fiscal esta en
  `docs/ERP_ADMINISTRATIVO_FISCAL.md`; el codigo que lo implemente lo
  actualiza en el mismo commit.
