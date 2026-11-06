# Sesja021 — korekta cyklu w godzinie zmiany czasu

Kod0207afb5bf/CI42305590784 SUCCESS/300PASS. W końcowym przeglądzie wykryto
rzeczywisty błąd: dodanie dnia do02:30 przed wiosenną zmianą strefy tworzyło nieistniejący
slot; normalizacjaUTC powodowała trwały dryf kolejnych zadań do03:30.

Generator zachowuje lokalną godzinę, pomija nieistniejące wystąpienie i wybiera pierwsze
wystąpienie godziny jesiennej. Nie tworzy zadania w nieistniejącym terminie. Reguła jest
jawna; nie jest to wysyłka ani wizyta potwierdzona. Po3 niewyznaczalnych wystąpieniach
odmawia zamiast nieskończonej pętli. Brak nowej migracji i nowych tabel.

Nowe4 czyste testy (dziennygap, tygodniowygap, jesień, zwykła godzina przezDST), bezDB
lubHTTP. `pytest -q tests/test_native_recurrence.py`:4passed/0failed/0skipped/0.46s.
Dotychczasowa integracja zadania cyklicznego z API pozostaje w pełnymCI.
Compileall/diff-checkPASS. Łącznie45 nowych przypadków od015, pełnyCI końcowegoSHA
wymagany przedPASS. Produkcyjne wydanie nadalBLOCKED.

Wszystkie ograniczenia020 pozostają: RPO60/SQL004/magazyn-klucz/rollback-handoff,
brak push/dragdrop/fizycznegoiPhone i zatwierdzonej retencji. Nie zmieniono produkcji,
Render/sieci/sekretów,005 ani zakresuA. Bez merge/deploy/eksportów/restore/Meta/Google/DM/
nowych płatnych zasobów; Focus1/2 nietknięte. Szacunek≥5 podstawowych+≥1DM.
Następny etap: retencja i skala/paginacja. RESUME i raport poranny zawierają punkt
wznowienia. Nie deklarujemy pracy w tle po zakończeniu wykonania.
