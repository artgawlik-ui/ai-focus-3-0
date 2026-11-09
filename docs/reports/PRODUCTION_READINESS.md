# Ai Focus3.0.4 — gotowość produkcyjna, sesja024

**Decyzja produkcyjna: BLOCKED.** Zielony kod i testy syntetyczne nie potwierdzają
aktualnej integralności klientów, skutecznego RPO ani możliwości rollbacku w Render.
Wejście80f4652: pełne CI42647145719/42647135285 SUCCESS,359 PASS. Kandydat024 wymaga
własnego pełnego CI dokładnego SHA. PR #3 Draft, bez zgody na merge/deploy.

Dowody bieżące: [metadane024](../sessions/session-024/provider-readonly.json),
[plan SQL](../sessions/session-024/SQL_EXECUTION_PLAN.md),
[rollout/rollback](../sessions/session-024/ROLLOUT_ROLLBACK.md),
[kryteria](../sessions/session-024/ACCEPTANCE.md), [raport](../sessions/session-024/REPORT.md).

## Kod i próby izolowane

| Bramka | Status | Konkretny dowód | Brakujący element | Ryzyko / granica | Następna bezpieczna czynność | Zgoda właściciela |
|---|---|---|---|---|---|---|
| Kod wejściowy i Draft PR | PASS | HEAD80f4652 i oba pełne CI SUCCESS, PR3Draft | brak dla wejścia | nie jest nowym SHA024 | sprawdzić CI końcowego SHA | nie, rutynowa |
| Pakowanie profilu native | PASS lokalny | rzeczywisty build COPY z Dockerfile, bez sieci; baseline80f nie zawiera ini, poprawiony artefakt odkrywa004 i007 | pełny obraz środowiska Render | test COPY nie buduje warstw npm/pip/OS i nie jest testem Render | pełny CI, potem zatwierdzony build wydania | testy nie; wydanie tak |
| Atomowość handoff na007 | PASS lokalny | dwa realne procesy, SIGTERM/kill przed commit;0 albo4 wpisy, przejęcie bez duplikatów; restart bez zmian | produkcyjne zakończenie wszystkich instancji | d15265b nie zna nowego protokołu | zachować pauzę do dowodu wyjścia starych | testy nie; produkcja tak |
| Szkice i opt-out przy przejęciu | PASS lokalny |1 szkic dozwolony, zablokowany job failed,0 szkiców zablokowanego klienta; liczba kontaktów bez zmian | dowód bieżącej kolejki produkcyjnej | testy tylko syntetyczne | pakiet A po udostępnieniu kanału | A już jest; kanał/ID wymagane |
| Odczyt starego API na007 | PASS ograniczony | d15265b: health200, prywatne API401, autoryzowany syntetyczny odczyt3 salonów; count/SHA21 tabel bez zmian | rzeczywisty obraz i env starego deployu | bieżące zależności testowe; bez starego workera/start.sh | nie traktować tego jako zwykłego rollbacku | test nie; wykonanie tak |
| Zwykły startup d15265b na007 | BLOCKED | rzeczywisty stary Alembic odrzuca007;21 fingerprintów bez zmian | zatwierdzona zgodna ścieżka startu | downtime lub niekontrolowany stary worker | wybrać zgodny artefakt lub kontrolowany API-only rebuild, bez downgrade | tak, decyzja o ryzyku i wydaniu |
| Pełny końcowy CI024 | BLOCKED do wyniku | lokalna regresja63 PASS,5 nowych przypadków | dokładne końcowe CI: backend/build/Chromium/WebKit/audyty | nie dziedziczyć359 z wejścia | wykonać push i zaczekać na pełny SUCCESS | nie |

## Rzeczywiste warunki produkcji

| Bramka | Status | Konkretny dowód | Brakujący element | Ryzyko | Następna bezpieczna czynność | Zgoda właściciela |
|---|---|---|---|---|---|---|
| Dostęp wewnętrzny SQL | BLOCKED | revision5 enforced/current; TCP=[],VPN=false;0 SSH/SQL; PG publiczna allowlista pusta | działający zatwierdzony Shell/SSH, zaufany host i autoryzacja | alternatywny kanał przekroczyłby A | administrator udostępnia już zatwierdzony wewnętrzny kanał, bez publicznego DB | wykonanie sieci/kluczy poza sesją; nie zmieniono |
| Bieżące004/17 tabel i integralność | BLOCKED | pakiet4SELECT nietknięty; generator zgodny i testy syntetyczne | aktualny wynik jednej READ ONLY REPEATABLE READ transakcji | snapshot005 nie opisuje dzisiejszych danych | tylko pakiet005 po odblokowaniu kanału; STOP przy innym schemacie | A udzielona, zakres nie rozszerzony |
| Konta i sesje techniczne | BLOCKED | historyczny export004 miał wyłączone konto; świeżego odczytu brak | prywatnie zatwierdzone ID i wynik approved accounts SELECT | aktywna stara sesja lub błędna tożsamość | prywatne potwierdzenie operatora; nie odgadywać i nie ujawniać ID | tak, prywatne potwierdzenie |
| Bieżący kod i autodeploy | PASS metadanych | RenderGET: live d15265b/dep-dbjhl6jbc2fs73crj65g; branch main, autoDeploy=no,1 instancja | brak dla tego odczytu | metadata nie potwierdzają zdrowia aplikacji/kolejki | przed wydaniem powtórzyć ograniczony odczyt | rutynowy odczyt tak, wykonany; deploy nie |
| PITR jako funkcja | PASS dokumentacji | płatny PG17 0.1c-256mb,1GB; dokumentacja mówi o ciągłych backupach płatnych baz | aktualny status recovery i workspace billing tier | available bazy ≠ AVAILABLE PITR ≠ odzyskanie | odczyt Recovery w oficjalnym panelu lub potwierdzenie providera | odczyt nie wymaga nowego kosztu; konto/operator |
| RPO≤60 min i rzeczywisty punkt | BLOCKED | get_postgres nie ma latest point/WAL lag; historyczny AVAILABLE/startsAt jest z006 | aktualny skuteczny punkt≤3600s i dowód odtworzenia/replay oraz monitoring świeżości | ostatnie10min niedostępne w UI nie są gwarancją lag≤60min | odczytać latest recoverable timestamp; dopiero potem osobno zatwierdzony izolowany test | restore/PITR/koszt wymaga nowej zgody |
| Aktualność eksportu005 | BLOCKED jako bieżące RPO | zweryfikowany snapshot2026-11-01T18:25Z,17 tabel/23 rekordy/004 | aktualna trwała kopia; obecna dostępność pliku w Render | snapshot starszy niż60min i niż7-dniowa retencja providera; nie zakładać obecności | bez eksportu: sprawdzić metadane zachowanych punktów | nowa kopia wymaga osobnej zgody |
| Magazyn niezależnej kopii | BLOCKED | brak aktualnego dowodu obiektu/lifecycle/odczytu; kod offsite opt-in | zaakceptowany magazyn, DPA/region/retencja, obiekt z hashem i dostępem recovery | utrata usługi/konta/providera | operator dostarcza niesekretne metadane istniejącego magazynu | nowa usługa/koszt/konfiguracja: tak |
| Trwałość i odzyskiwalność klucza | BLOCKED | format FOCUS3B1/AES-GCM+scrypt w kodzie; sekretów nie pobierano | niezależna kontrolowana kopia klucza, wersja i sprawdzony dostęp operatora | zaszyfrowany plik bez klucza jest nieodtwarzalny | potwierdzić procedurę odzyskania klucza w zatwierdzonym menedżerze | właściciel/operator, bez wartości w rozmowie |
| Dostępność artefaktu/env rollbacku | BLOCKED | stary deploy live i Git dostępny; API nie wystawia eligibility ani env snapshot | zachowany artefakt i bezpieczna konfiguracja celu | rollback odtwarza dawny start/env; nie jest restore DB | Dashboard → Deploys → sprawdzić możliwość i cel bez uruchamiania | wykonanie rollbacku/rebuild/config: tak |
| Pierwszy produkcyjny handoff | BLOCKED | lokalne próby PASS, stary kod nie respektuje pauzy | dowód końca starych procesów i kontrola kolejki po zatrzymaniu | równoległe niezgodne konsumery, powtórne analizy | plan ROLLOUT_ROLLBACK; żadnej aktywacji w tej sesji | tak, wymaga zatwierdzonego wydania |
| Efektywne flagi i retencja produkcji | BLOCKED dla świeżego potwierdzenia | kod domyślnie OFF; nie pobierano env; historyczne stany nie są bieżące | sprawdzone flagi poszczególnych modułów i start/retencja | MetaOFF nie zatrzymuje maintenance; pauza nie blokuje bootstrap/migracji/offsite | operator sprawdza flagi bez ujawnienia sekretów; wszystkie nowe moduły OFF | zmiana konfiguracji lub uruchomienie: tak |
| Zgoda wydania | BLOCKED | PR3 pozostaje Draft; brak pisemnej zgody na merge/deploy | osobna zgoda na SHA, schemat i plan | nieautoryzowany rollout | przedstawić zamknięte dowody, potem poprosić o konkretną zgodę | tak |

## Decyzje, których nie podjęto za właściciela

Najpierw wykorzystać istniejący PITR do potwierdzenia punktu; brak dowodu nie uzasadnia
upgrade. Test PITR tworzy nową instancję, więc wymaga planu izolacji, aktualnej wyceny
oraz osobnej zgody. Nie uruchomiono testu, nowego eksportu ani nowej usługi. Nie przyjęto
wyjątku RPO dla utraty całego konta Render. Dzienny offsite (86400s; retry3600s), nawet
włączony, nie gwarantuje RPO60; backup blokuje zapisy SHARE i buforuje dump w pamięci.
Nie zmieniano harmonogramu, klucza, wartości env, uprawnień ani konfiguracji sieci.

Źródła sprawdzone2026-11-09 (HTTP200, odczytano odpowiednie sekcje):
https://render.com/docs/postgresql-backups.md — PITR płatnych baz, okno3/7dni wgworkspace,
wyłączenie ostatnich10min, nowa instancja recovery, logical exports7dni;
https://render.com/docs/rollbacks.md — retencja artefaktów i snapshot konfiguracji;
https://render.com/docs/private-network.md — wewnętrzna sieć Render, nie publiczne obejście.
Historyczne dowody snapshotu/recovery: session005 i session006, bez ponownego restore.
