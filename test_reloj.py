"""Casos que fijan las ranuras del reloj (espejo de `due_this_hour` de exi-juarez)."""
from datetime import date, datetime, timedelta

import reloj

LUNES = date(2026, 9, 14)


def horas(dia, minuto):
    return sorted(r.hour for r in reloj.ranuras(dia) if r.minute == minuto)


def test_ventana_de_campo_intacta():
    v = [r for r in reloj.ranuras(LUNES) if r.minute in (14, 44)]
    assert len(v) == 20
    assert (v[0].hour, v[0].minute, v[-1].hour, v[-1].minute) == (8, 14, 17, 44)


def test_la_hora_20_solo_el_miercoles():
    assert [d for d in range(4) if 20 in horas(LUNES + timedelta(days=d), 9)] == [2]


def test_cada_hora_nocturna_tiene_un_dia_habil():
    cubiertas = set()
    for d in range(4):
        cubiertas |= set(horas(LUNES + timedelta(days=d), 9))
    assert set(range(18, 24)) | set(range(0, 8)) <= cubiertas


def test_fin_de_semana_cada_hora():
    assert horas(LUNES + timedelta(days=5), 9) == list(range(24))


def test_no_dispara_fuera_de_ranura_en_dia_habil():
    # Martes 20:09 local = 02Z: ni alimentadoras (02 % 5) ni rejilla del martes ((2 - 1) % 3).
    assert 20 not in horas(LUNES + timedelta(days=1), 9)


def test_el_reloj_nunca_se_queda_sin_ranura():
    t = datetime(2026, 9, 14, 0, 0, tzinfo=reloj.TZ)
    ultima = None
    for _ in range(400):
        r = reloj.proxima_ranura(t, ultima)
        assert r is not None and r > t - timedelta(seconds=31)
        # El hueco mayor es de 3 h 05: miercoles 05:09 -> 08:14, primera ranura de ventana.
        assert (r - t) < timedelta(hours=3, minutes=10)
        t, ultima = r, r


def test_cierre_de_ventana_pasa_a_la_noche():
    t = datetime(2026, 9, 17, 17, 50, tzinfo=reloj.TZ)      # jueves, tras la ultima ranura
    assert reloj.proxima_ranura(t).strftime("%a %H:%M") == "Thu 18:09"


# --- calendario "presupuesto" (propuesta 2026-09-29, espejo de exi-juarez) -------------------
def test_presupuesto_espeja_a_exi_juarez(monkeypatch):
    monkeypatch.setattr(reloj, "CALENDARIO", "presupuesto")
    # Valores calculados en exi-juarez con `rejilla_presupuesto` (hora local de Juarez).
    assert horas(date(2026, 10, 5), 9) == [3, 7, 11, 15, 19, 23]
    assert horas(date(2026, 10, 6), 9) == [0, 4, 8, 12, 16, 20]


def test_presupuesto_cubre_las_168_celdas_en_4_semanas(monkeypatch):
    monkeypatch.setattr(reloj, "CALENDARIO", "presupuesto")
    celdas = set()
    for k in range(28):
        d = date(2026, 10, 5) + timedelta(days=k)
        celdas |= {(d.weekday(), h) for h in horas(d, 9)}
    assert len(celdas) == 168


def test_presupuesto_sin_ventana_de_campo(monkeypatch):
    monkeypatch.setattr(reloj, "CALENDARIO", "presupuesto")
    assert not [r for r in reloj.ranuras(LUNES) if r.minute in (14, 44)]
    assert all(len(reloj.ranuras(LUNES + timedelta(days=k))) == 6 for k in range(14))


def test_presupuesto_nunca_se_queda_sin_ranura(monkeypatch):
    monkeypatch.setattr(reloj, "CALENDARIO", "presupuesto")
    t = datetime(2026, 10, 1, 0, 0, tzinfo=reloj.TZ)
    ultima = None
    for _ in range(300):
        r = reloj.proxima_ranura(t, ultima)
        assert r is not None and (r - t) <= timedelta(hours=8)
        t, ultima = r, r


def test_por_defecto_sigue_el_calendario_vigente():
    assert reloj.CALENDARIO == "vigente"
