# Sesja 005 — kryteria przed pracą

1. Potwierdzić HEAD/checks i zachować Draft PR bez merge/deploy.
2. Oznaczyć jako OWNER_VERIFIED test rzeczywistego eksportu 2026-11-01: PostgreSQL 17.11, 17 tabel, 23 rekordy, 004. Nie uznać za stan bieżący lub kompletny manifest bez identyfikacji eksportu/SHA.
3. Przygotować i przetestować minimalny zestaw SELECT: revision/PG/tabele, agregaty kont/sesji, liczności i SHA wszystkich 17 tabel; brak PII/sekretów. Odczyt w REPEATABLE READ READ ONLY i ROLLBACK, timeouty; bez DDL/DML na produkcji.
4. Sprawdzić tylko istniejące eksporty/recovery/deploye przez GET; nie tworzyć eksportu, restore, restartu ani zasobów. Jeżeli dostępny eksport pobieramy, wyłącznie prywatny katalog i izolowany lokalny restore bez aplikacji/sieci; brak danych i URL podpisanych w repo/logach.
5. Rozdzielić odtwarzalność snapshotu od jego aktualności i od niezależnego szyfrowanego magazynu/klucza.
6. Plan wydania Meta OFF z pracującym workerem/retencją, ryzykiem nakładania instancji, warunkami STOP i kontrolami count/SHA po wdrożeniu; żadnego uruchomienia produkcyjnego.
7. Raport z macierzą zamkniętych/otwartych blokad, dowodami, dokładnymi zgodami/czynnościami właściciela i decyzją READY/BLOCKED. Licznik 5 podstawowych + ≥1 DM bez zmniejszenia za przygotowanie.
