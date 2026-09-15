# exi-reloj

Reloj de la cosecha de EXi (Auralis Lab). **No contiene datos.** Solo espera y pide a GitHub que corra la cosecha del repositorio privado del proyecto en cada ranura en que hay algo que consultar.

- **Dentro de la ventana de campo** (lunes a jueves, 08:00–18:00 hora de Ciudad Juárez) dispara cada 30 min.
- **Fuera de la ventana** dispara a las hh:09 de las horas en que la cosecha tiene puntos pendientes: cada hora de viernes a domingo, y de lunes a jueves en una rejilla de 3 h que rota por día para que ninguna hora nocturna quede sin fechas.

Existe porque GitHub descarta buena parte de los disparos programados (`schedule`) de ese repositorio, y tanto las tomas de video de campo como la cobertura diel del panel necesitan registros a su hora. Los disparos manuales (`workflow_dispatch`) no se descartan, pero alguien tiene que esperar entre uno y otro: esa espera la hace este repositorio. **El reloj corre sin parar y se releva a sí mismo**; el `schedule` solo sirve de arranque de respaldo si la cadena se rompe.

- `reloj.py`: duerme hasta la siguiente ranura y dispara. Se releva antes del límite de 6 h por job. La regla de fuera de ventana espeja la de la cosecha; si cambia allá, cambia aquí.
- `test_reloj.py`: casos que fijan las ranuras (`python -m pytest`).
- `.github/workflows/reloj.yml`: arranque de respaldo, relevo y latido.
- `latido.md`: una línea por job, con su inicio, su fin y cuántas ranuras disparó o falló.

Requiere el secreto `EXI_DISPATCH_TOKEN`: un token de acceso fino con permiso **Actions: read and write** sobre el repositorio del proyecto, y nada más.
