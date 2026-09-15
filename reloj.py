"""Reloj de la cosecha EXi: dispara `acquire.yml` de exi-juarez en cada ranura en que hay algo que cosechar.

Por que existe
--------------
Desde el 27-ago-2026 GitHub descarta la mayoria de los `schedule` del repo privado exi-juarez
(~6 de 48 corridas diarias), y las tomas de video de campo (lun-jue, 08:00-18:00 hora de Juarez,
sin fecha avisada) necesitan un tick del panel a <= 15 min. Los `workflow_dispatch` no se
descartan, pero alguien tiene que esperar entre uno y otro: aqui la espera la hace este job, en
un repo publico donde los minutos de Actions no se cobran.

Que hace
--------
Corre sin parar y se releva antes del limite de 6 h por job, de modo que solo el primer arranque
depende de un `schedule`. Dispara en dos clases de ranura, en hora de Juarez:

- ventana de campo (lun-jue 08:00-18:00): cada 30 min en :14/:44; el runner de exi-juarez tarda
  ~1 min y el tick cae en :15/:45, que son las ranuras de `src/acquire_tomtom.py`.
- fuera de ventana: a las hh:09 de cada hora en que la cosecha tiene puntos que consultar. Son
  las troncales cada hora de viernes a domingo, y de lunes a jueves la rejilla de 3 h ROTADA
  por dia (desfase = dia % 3). A eso se suman las alimentadoras cuando la hora UTC es multiplo
  de 5.

La regla de fuera de ventana ESPEJA `due_this_hour` de exi-juarez, que es privado y cuyo
contenido este token no lee. Si cambia alla, cambia aqui; `test_reloj.py` fija los casos. Ver
`docs/asiento_rejilla_rotada_2026-09-14.md` en exi-juarez.

Desde el 2026-09-14: ese primer dia de ventana GitHub descarto todos los arranques de la
manana (el reloj entro a las 12:21) y la cobertura diel de G0 cayo a 23/24 por la hora 20:00,
que la rejilla fija de 3 h no tocaba nunca.

No decide que consultar ni gasta cuota: eso vive en exi-juarez, que es idempotente.

Salidas (GITHUB_OUTPUT): relevo=true|false · disparos=N · fallos=N · inicio · fin
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Ciudad_Juarez")
DIAS_VENTANA = {0, 1, 2, 3}         # lunes=0 ... jueves=3
INI, FIN = 8 * 60, 18 * 60          # ventana en minutos del dia, hora local
CADENCIA = 30
DESFASE = 14                        # dispara a :14/:44 -> tick en :15/:45
MINUTO_FUERA = 9                    # fuera de ventana dispara a las hh:09
PASO_REJILLA = 3                    # troncales fuera de ventana en dias de ventana
PASO_ALIM = 5                       # alimentadoras: horas UTC multiplo de 5
REPO = "Pierre-du-Lioncourt/exi-juarez"
WORKFLOW = "acquire.yml"
RAMA = "main"
LIMITE_MIN = float(os.environ.get("LIMITE_MIN", "340"))   # el job muere a los 355


def en_ventana(t: datetime) -> bool:
    return t.weekday() in DIAS_VENTANA and INI <= t.hour * 60 + t.minute < FIN


def hay_cosecha_fuera(t: datetime) -> bool:
    """Espejo de `due_this_hour` de exi-juarez para una corrida a la hora local de `t`."""
    h_utc = t.astimezone(timezone.utc).hour
    if h_utc % PASO_ALIM == 0:
        return True
    if t.weekday() not in DIAS_VENTANA:
        return True
    return (h_utc - t.weekday() % PASO_REJILLA) % PASO_REJILLA == 0


def ranuras(dia) -> list[datetime]:
    base = datetime(dia.year, dia.month, dia.day, tzinfo=TZ)
    out = []
    for h in range(24):
        r = base + timedelta(hours=h, minutes=MINUTO_FUERA)
        if not en_ventana(r) and hay_cosecha_fuera(r):
            out.append(r)
    if dia.weekday() in DIAS_VENTANA:
        m = INI + DESFASE
        while m < FIN:
            out.append(base + timedelta(minutes=m))
            m += CADENCIA
    return sorted(out)


def proxima_ranura(t: datetime, despues_de: datetime | None = None) -> datetime | None:
    """La siguiente ranura desde `t`, hoy o en los dos dias siguientes.

    Los 30 s de tolerancia recogen una ranura que se acaba de pasar al arrancar el job.
    `despues_de` excluye la ya disparada: sin el, la tolerancia devolvia LA MISMA ranura
    durante 30 s y el reloj disparaba en rafaga (lo encontro la prueba del 2026-09-10).
    """
    for dd in range(3):
        for r in ranuras((t + timedelta(days=dd)).date()):
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
    arranque = datetime.now(TZ)
    disparos = fallos = 0
    ultima = None
    if os.environ.get("PRUEBA", "").lower() == "true":
        # Disparo inmediato para verificar el token sin esperar a una ranura (arranque
        # manual con prueba=true; útil también al renovar el token).
        ok = dispara(token)
        disparos += ok
        fallos += not ok
        print("%s · PRUEBA inmediata · %s" % (datetime.now(TZ).strftime("%H:%M:%S"),
                                             "disparado" if ok else "FALLO"), flush=True)
    while True:
        t = datetime.now(TZ)
        r = proxima_ranura(t, ultima)
        espera = max(0.0, (r - t).total_seconds()) if r else float("inf")
        if (time.monotonic() - inicio + espera) / 60 > LIMITE_MIN:
            print("la siguiente ranura (%s) cae despues del limite del job: relevo"
                  % (r.strftime("%a %H:%M") if r else "ninguna"), flush=True)
            break
        time.sleep(espera)
        ultima = r
        ok = dispara(token)
        disparos += ok
        fallos += not ok
        print("%s · ranura %s · %s" % (datetime.now(TZ).strftime("%H:%M:%S"),
                                        r.strftime("%a %H:%M"), "disparado" if ok else "FALLO"),
              flush=True)
    salida(relevo="true", disparos=disparos, fallos=fallos,
           inicio=arranque.strftime("%Y-%m-%d %H:%M"),
           fin=datetime.now(TZ).strftime("%Y-%m-%d %H:%M"))
    if fallos and not disparos:
        sys.exit(1)             # en rojo si ninguna ranura se pudo disparar; el relevo sigue


if __name__ == "__main__":
    main()
