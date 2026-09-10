# exi-reloj

Reloj de la cosecha de EXi (Auralis Lab). **No contiene datos.** Sólo espera y, cada 30 min
dentro de la ventana de campo (lunes a jueves, 08:00–18:00 hora de Ciudad Juárez), pide a GitHub
que corra la cosecha del repositorio privado del proyecto.

Existe porque GitHub descarta buena parte de los disparos programados (`schedule`) de ese
repositorio, y las tomas de video de campo necesitan un registro del panel de tránsito a no más de
15 minutos. Los disparos manuales (`workflow_dispatch`) no se descartan, pero alguien tiene que
esperar entre uno y otro: esa espera la hace este repositorio.

- `reloj.py`: duerme hasta la siguiente ranura y dispara; se releva antes del límite de 6 h por job.
- `.github/workflows/reloj.yml`: arranques programados, relevo y latido diario.
- `latido.md`: una línea por día de ventana con cuántas ranuras se dispararon.

Requiere el secreto `EXI_DISPATCH_TOKEN`: un token de acceso fino con permiso **Actions: read and
write** sobre el repositorio del proyecto, y nada más.
