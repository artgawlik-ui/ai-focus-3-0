"""Brak połączeń: porównanie dostarczonych odcisków przed/po operacji."""
import re


def compare_snapshots(before,after):
    """Nie ujawnia odcisków ani danych; odrzuca pusty lub niepełny punkt odniesienia."""
    for snapshot in (before,after):
        if not isinstance(snapshot,dict) or not snapshot:raise ValueError('Brak poprawnego punktu odniesienia')
        for name,item in snapshot.items():
            if not re.fullmatch('[a-z_][a-z0-9_]*',name) or not isinstance(item,dict):raise ValueError('Niepoprawny format manifestu')
            if type(item.get('count')) is not int or item['count']<0 or not re.fullmatch('[a-f0-9]{64}',str(item.get('sha256',''))):raise ValueError('Niepoprawny format manifestu')
    if before!=after:raise ValueError('Integralność niepotwierdzona; wstrzymaj odbiór i wyjaśnij różnicę')
    return {'status':'PASS','tables':len(before),'counts_equal':True,'sha256_equal':True}
