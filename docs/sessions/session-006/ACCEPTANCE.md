# Sesja 006 — kryteria przed kontrolą

**Zatwierdzona decyzja właściciela: RPO = 60 minut (3600 s).** Zmiana wymagania, nie zgoda na zakup/restore/eksport/deploy.

1. Odczytać bieżący plan/retencję/metadane PITR i eksportów tylko GET; brak nowego eksportu, restore i zmian.
2. Zweryfikować aktualne oficjalne dokumenty planów/backups/cennika; odróżnić compute plan od workspace plan.
3. Nie wnioskować o najnowszym skutecznym punkcie z samego AVAILABLE/startsAt. Ustalić, czy istnieje dowód latest recoverable timestamp i odtwarzalności w dopuszczonym środowisku.
4. Obliczyć wiek ostatniego istniejącego eksportu; spełnienie progu dotyczy czasu snapshotu, nie momentu pobrania/restore.
5. Przygotować szyfrowanie/magazyn/klucz/retencję/test restore i najprostszy wariant osiągnięcia RPO, bez aktywacji i kosztów bez zgody.
6. Raport READY/BLOCKED, warunki i ewentualne koszty do zatwierdzenia. Pozostałe blokady SQL/kont/rollback/workera nadal obowiązują.
