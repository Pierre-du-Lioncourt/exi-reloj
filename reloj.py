"""Reloj de la cosecha EXi: dispara `acquire.yml` de exi-juarez cada 30 min en la ventana de campo.

Por que existe
--------------
Desde el 27-ago-2026 GitHub descarta la mayoria de los `schedule` del repo privado exi-juarez
(~6 de 48 corridas diarias), y las tomas de video de campo (lun-jue, 08:00-18:00 hora de Juarez,
sin fecha avisada) necesitan un tick del panel a <= 15 min. Los `workflow_dispatch` no se
descartan, pero alguien tiene que esperar 30 min entre uno y otro: aqui la espera la hace este
job, en un repo publico donde los minutos de Actions no se cobran.

Que hace
--------
Duerme hasta la siguiente ranura (08:14, 08:44 ... 17:44 local; el runner de exi-juarez tarda ~1
min en arrancar y el tick cae en :15/:45, que son las ranuras de `src/acquire_tomtom.py`) y ahi
pide la corrida. Antes del limite de 6 h por job se detiene y avisa al workflow que se relance.
No decide que consultar ni gasta cuota: eso vive en exi-juarez, que es idempotente por ventana.

Salidas (GITHUB_OUTPUT): relevo=true|false · disparos=N · fallos=N
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Ciudad_Juarez")
DIAS = {0, 1, 2, 3}                 # lunes=0 ... jueves=3
INI, FIN = 8 * 60, 18 * 60          # ventana en minutos del dia, hora local
CADENCIA = 30
DESFASE = 14                        # dispara a :14/:44 -> tick en :15/:45
REPO = "Pierre-du-Lioncourt/exi-juarez"
WORKFLOW = "acquire.yml"
RAMA = "main"
LIMITE_MIN = float(os.environ.get("LIMITE_MIN", "340"))   # el job muere a los 355


def ranuras(dia) -> list[datetime]:
    base = datetime(dia.year, dia.month, dia.day, tzinfo=TZ)
    out, m = [], INI + DESFASE
    while m < FIN:
        out.append(base + timedelta(minutes=m))
        m += CADENCIA
    return out


def proxima_ranura(t: datetime, despues_de: datetime | None = None) -> datetime | None:
    """La siguiente ranura de HOY, o None si hoy ya no hay (o no es dia de ventana).

    Los 30 s de tolerancia recogen una ranura que se acaba de pasar al arrancar el job.
    `despues_de` excluye la ya disparada: sin el, la tolerancia devolvia LA MISMA ranura
    durante 30 s y el reloj disparaba en rafaga (lo encontro la prueba del 2026-09-10).
    """
    if t.weekday() not in DIAS:
        return None
    for r in ranuras(t.date()):
        if r >= t - timedelta(seconds=30) and (despues_de is None or r > despues_de):
            return r
    return None


def dispara(token: str) -> bool:
    """POST directo al endpoint de dispatch: sólo exige Actions: write.

    `gh workflow run` sin rama consulta antes por GraphQL la rama por defecto del repo,
    y eso pide lectura de contenido, que el token fino no tiene a propósito. La primera
    ranura del 2026-09-10 falló así («Resource not accessible by personal access token
    (repository.defaultBranchRef)»).
    """
    env = dict(os.environ, GH_TOKEN=token)
    for intento in range(3):
        r = subprocess.run(["gh", "api", "-X", "POST",
                            f"repos/{REPO}/actions/workflows/{WORKFLOW}/dispatches",
                            "-f", f"ref={RAMA}"],
                           env=env, capture_output=True, text=True)
        if r.returncode == 0:
            return True
        print("  intento %d fallo: %s" % (intento + 1, (r.stderr or r.stdout).strip()), flush=True)
        time.sleep(20 * (intento + 1))
    return False


def salida(**kv) -> None:
    ruta = os.environ.get("GITHUB_OUTPUT")
    if ruta:
        with open(ruta, "a", encoding="utf-8") as f:
            for k, v in kv.items():
                f.write("%s=%s\n" % (k, v))
    print(" · ".join("%s=%s" % kv for kv in kv.items()), flush=True)


def main() -> None:
    token = os.environ.get("EXI_DISPATCH_TOKEN", "")
    if not token:
        sys.exit("Falta el secreto EXI_DISPATCH_TOKEN (token fino con Actions: write sobre "
                 "exi-juarez). Sin el, el reloj no puede disparar nada.")
    inicio = time.monotonic()
    disparos = fallos = 0
    relevo = False
    ultima = None
    if os.environ.get("PRUEBA", "").lower() == "true":
        # Disparo inmediato para verificar el token sin esperar a una ranura (arranque
        # manual con prueba=true; útil también al renovar el token).
        ok = dispara(token)
        print("%s · PRUEBA inmediata · %s" % (datetime.now(TZ).strftime("%H:%M:%S"),
                                             "disparado" if ok else "FALLO"), flush=True)
        if not ok:
            salida(relevo="false", disparos=0, fallos=1)
            sys.exit(1)
    while True:
        t = datetime.now(TZ)
        r = proxima_ranura(t, ultima)
        if r is None:
            print("%s · sin ranuras pendientes hoy: el reloj termina" % t.strftime("%a %H:%M"),
                  flush=True)
            break
        espera = max(0.0, (r - t).total_seconds())
        if (time.monotonic() - inicio + espera) / 60 > LIMITE_MIN:
            print("la siguiente ranura (%s) cae despues del limite del job: relevo"
                  % r.strftime("%H:%M"), flush=True)
            relevo = True
            break
        time.sleep(espera)
        ultima = r
        ok = dispara(token)
        disparos += ok
        fallos += not ok
        print("%s · ranura %s · %s" % (datetime.now(TZ).strftime("%H:%M:%S"),
                                        r.strftime("%H:%M"), "disparado" if ok else "FALLO"),
              flush=True)
    salida(relevo=str(relevo).lower(), disparos=disparos, fallos=fallos)
    if fallos and not disparos:
        sys.exit(1)             # que la corrida quede en rojo si ninguna ranura se pudo disparar


if __name__ == "__main__":
    main()
