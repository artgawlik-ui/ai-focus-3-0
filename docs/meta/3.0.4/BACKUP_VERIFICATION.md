# Issue #4 — weryfikacja eksportu PostgreSQL

**Eksport i lokalny test odtworzenia: PASS.** Nie wykonano odtwarzania produkcji, PITR, cutover, deploy ani zapisu do produkcyjnej bazy. Poniższe wyniki dotyczą **punktu reprezentowanego przez eksport**, a nie aktualnych, zmieniających się rekordów produkcyjnych.

## Pochodzenie i czas

- Źródło: `ai-focus-3-0-db`, `dpg-dbh1b0gm7kps73f0p2m0-a`, PostgreSQL 17, Frankfurt.
- Odczyt istniejącą autoryzacją Render przez oficjalne **GET /postgres/{postgresId}/export**. Nie wywołano POST tworzącego eksport ani żądania recovery.
- Eksport identyfikowany przez API jako `dpg-dbh1b0gm7kps73f0p2m0-a/2026-11-01T12:41Z`, `createdAt=2026-11-01T12:41:00Z` = **13:41 Europe/Warsaw**. Znaleziono dokładnie jeden pasujący eksport.
- TOC podaje **Archive created at 2026-11-01 12:42:47 UTC** = 13:42:47 Europe/Warsaw. Czas utworzenia zadania eksportu nie jest tym samym co rozpoczęcie dumpa. Dokładnego czasu/LSN uzyskania migawki MVCC nie znamy.
- `pg_dump` i źródłowy PostgreSQL: **17.11**. Nazwa bazy w TOC odpowiada oczekiwanemu `ai_focus_3_0_db`.

Podpisany URL otrzymano wyłącznie w pamięci procesu. Osobny klient HTTPS bez nagłówka autoryzacji Render pobrał plik; walidowano HTTPS, docelową domenę i przekierowania. Nie zapisano URL, query ani tokenów w repo, logach, issue i PR. Lokalny katalog był 0700, plik 0600. Po weryfikacji usunięto plik i ręcznie rozpakowane kopie; oryginalny eksport w Render nie został usunięty.

## Archiwum

| Kontrola | Wynik |
|---|---|
| Format rzeczywisty | gzip → tar → PostgreSQL DIRECTORY, nie tylko zgodne rozszerzenie |
| Rozmiar pobrany | **8 993 bajty**, zgodny z Content-Length |
| SHA-256 | `093ab561995be1f5af8383610b7b725113950a592a466ed14b5a348ad4a4f42d` |
| gzip CRC / pełne EOF | PASS |
| Tar | 21 elementów, 18 plików zwykłych, 3 katalogi, 45 600 bajtów danych plików |
| TOC | 1 toc.dat; nagłówek 89 wpisów, lista wybranych obiektów 84 |
| Dane | 17 plików tabel, 17 sekcji COPY |
| Niebezpieczne elementy | Brak; traversal, ścieżki bezwzględne, symlinki, hardlinki, urządzenia, duplikaty i przekroczenia limitów są odrzucane |

SHA-256 obliczono po pobraniu; API nie dostarczyło niezależnego checksumu. Pochodzenie wynika z uwierzytelnionego API przypisanego do tej bazy i pobrania HTTPS. CRC, TOC, odtworzenie oraz niezależne porównanie danych weryfikują czytelność i kompletność logiczną; nie nazywamy tego podpisem kryptograficznym dostawcy.

Dowód: [export-provenance.json](issue4-evidence/export-provenance.json).

## Rzeczywiście wykonane odtworzenie

Narzędzie: `scripts/isolated_export_restore.py`, wywołane z lokalną ścieżką pliku i oczekiwanym SHA-256. Nie przyjmuje produkcyjnego URL bazy ani parametrów cutover. Nie pobiera danych z Render, nie wywołuje Meta, odmawia pracy w APP_ENV=production. Opcjonalna tożsamość właściciela była przekazana w pamięci przez `FOCUS_RESTORE_OWNER_EMAIL`, bez ujawniania wartości.

Środowisko: nowy lokalny kontener z już obecnego obrazu PostgreSQL 17, `--pull=never`, image digest zapisany w dowodzie. **NetworkMode=none**, bez portów i bind mountów hosta, bez proxy, `listen_addresses=''`, `--cap-drop=ALL`, no-new-privileges, read-only rootfs. Dane tylko w tmpfs; limit 512 MiB / 0,5 CPU. Log driver none; nie zapisuje się logów SQL z danymi. Nie startowano aplikacji, agentów, webhooków, cronów i preload extensions, max_worker_processes=0. Wszystkie siedem flag Meta ustawione na false i potwierdzone z konfiguracji kontenera.

`pg_restore --no-owner --no-acl --single-transaction --exit-on-error` odtworzył **nową bazę restored**. Pominięcie ownership/ACL jest zamierzone: test nie importuje ról/uprawnień źródłowych na hosta. Kontener oraz tymczasowe pliki usunięto. Docker był przypięty do lokalnego unix socketu, bez możliwości przełączenia przez DOCKER_HOST/CONTEXT na inny silnik.

### Porównanie danych i schematu

Dane źródłowe odczytano niezależnie jako sekcje COPY z `pg_restore --data-only --file=-`, bez wykonywania ich na produkcji i bez zapisu tekstu SQL. Dla każdej tabeli policzono rekordy i SHA-256 multizbioru skrótów wierszy COPY. Po restore wykonano COPY TO STDOUT z tymi samymi kolumnami: **17/17 fingerprintów i liczności zgodnych**. Powtórzone wiersze uwzględnia się wielokrotnie, kolejność fizyczna nie wpływa na hash. Dodatkowo zapisano fingerprinty kanonicznego row_to_json zgodne z metodą `scripts.backup.fingerprint` / READONLY-SQL.sql.

Schemat porównano z TOC i niezmienionymi modelami 3.0.3/3.0.4: **17 tabel, Alembic 004, 127 kolumn, 40 ograniczeń** (26 PK/UNIQUE i 14 FK), **8 osobnych indeksów** oraz 26 indeksów realizujących ograniczenia, łącznie 34. Sygnatury typów/nullability/kluczy/indeksów zgodne; definicje katalogowe zachowano wyłącznie jako hashe. Nie dodawano migracji ani danych do dumpa.

| Tabela | Rekordy eksport = restore |
|---|---:|
| activities | 8 |
| alembic_version | 1 |
| appointments | 1 |
| integration_links | 0 |
| jobs | 3 |
| login_attempts | 0 |
| salons | **1** |
| sessions | 7 |
| trainings | 0 |
| users | 2 |
| 7 tabel meta_* | po 0 |

**Nie potwierdzamy 118 salonów.** W wskazanym eksporcie bazy Focus 3.0 jest jeden rekord; nie badano zawartości Focus 1.0/2.0 i nie przeprowadzano migracji ich klientów.

Właściciel (zgodny z konfiguracją BOOTSTRAP_EMAIL, bez publikowania wartości): aktywny manager. Konto techniczne: 1 rekord, active=0; 0 sesji technicznych ważnych na moment czasu TOC. To **stan migawki**, nie nowy test logowania. Credential/inbox/refresh puste; nie było tokenów do odszyfrowywania ani rzeczywistych wiadomości do przetworzenia.

Pełne hashe i agregaty: [restore-verification.json](issue4-evidence/restore-verification.json). Pierwszy parser wymagał obsługi cytowanych identyfikatorów PostgreSQL 17; poprawiono go i dodano test. Przerwane próby usuwały kontener; końcowy wynik PASS pochodzi z pełnego ponownego przebiegu, a nie ręcznego zmienienia statusu.

## RPO / RTO i PITR

- Lokalny **pg_restore: 0,110 s**, pełna kontrola w ostatnim przebiegu **8,821 s**. Dotyczy pliku 8 993 B i opisanego lokalnego limitu, **nie produkcyjnego RTO** z provisioningiem, DNS, aplikacją i zatwierdzeniami.
- Produkcyjnego RPO ani RTO incydentu nie zmierzono. Znamy daty zadania eksportu i TOC, nie dokładny LSN MVCC. Nowe dane po punkcie eksportu nie są nim chronione.
- Oficjalny **GET /postgres/{postgresId}/recovery** zwraca **AVAILABLE**, **startsAt=2026-10-29T06:32:47Z**. Jest to rzeczywisty odczyt API, nie interpretacja kalendarza.
- API nie podaje górnej granicy. Dokumentacja nie pozwala wybrać ostatnich 10 minut, ale nie stanowi to pomiaru faktycznego najnowszego odtwarzalnego czasu. Pełne 72 h dla dowolnej godziny oraz górny zakres pozostają niepotwierdzone. Płatnego PITR nie uruchomiono.

Próba PITR po osobnej zgodzie: zapisać dokładny dostępny zakres z formularza Recovery; wybrać dopuszczony punkt; po przedstawieniu ceny utworzyć osobną recovery instance; nie podpinać aplikacji, nie kopiować aktywnych integracji/schedulerów; odczytowo porównać stan z wybranym punktem/WAL, wykonać sanity checks; nie robić cutover. Zakończenie i ewentualne usunięcie płatnej instancji również wymagają uzgodnionej procedury. W tym zadaniu dodatkowych płatnych zasobów: **0**.

## Źródła oficjalne i odtwarzalność

Odczyt 2026-11-01, HTTP 200:
- https://api-docs.render.com/reference/list-postgres-export.md — GET listy i URL pobrania;
- https://api-docs.render.com/reference/retrieve-postgres-recovery-info.md — AVAILABLE/startsAt, bez endsAt;
- https://render.com/docs/postgresql-backups.md — eksport directory, recovery do nowej instancji i ograniczenie 10 minut;
- https://api-docs.render.com/reference/retrieve-deploy.md — odczyt metadanych deployu; nie potwierdza retencji artefaktu rollbacku.

Publicznego/podpisanego linku pobrania nie umieszcza się w poleceniu ani pliku raportu. Ponowny test wymaga ponownego autoryzowanego pobrania oryginału; plaintext nie jest przechowywany w repo ani pozostawiony w tym środowisku. 15 nowych przypadków automatycznych testuje wyłącznie syntetyczne archiwa, a rzeczywisty dump służył tylko odtworzeniu i odczytowej kontroli integralności w odizolowanej kopii.
