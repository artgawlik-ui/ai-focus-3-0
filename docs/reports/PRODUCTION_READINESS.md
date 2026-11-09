# Sesja027 — aktualna decyzja: BLOCKED

Odczyt9listopada2026 (UTC w metadanych). Bazae37ce5d: oba pełne CI42686949414/42686938187
SUCCESS,380PASS. Nowa gałąź `fix/session-027-readonly-rollback` ma oddzielny Draft PR/CI;
nie przenosi wyniku380 na nowy kod. Kod0275e4188a ma własne obaCI SUCCESS/394PASS;
końcowy SHA (guardWebSocket/dokumentacja) sprawdzany osobno wPR #9. [Raport027](../sessions/session-027/REPORT.md),
[świeże metadane](../sessions/session-027/provider-readonly.json),
[szczegółowy plan i STOP](../sessions/session-027/ROLLOUT.md).

| Bramka027 | Status | Dowód / brakujący element | Dokładna czynność operatora / zgoda |
|---|---|---|---|
| Wejściowy kod PR3 | PASS | e37ce5d,oba pełneCI SUCCESS; PR3Draft | brak powtórnej symulacji; nowy kod wymaga własnego CI |
| Bieżący deploy i PG jako zasoby | PASS metadanych | RenderGET:d15265b live,autoDeploy=no,1instancja;PG17available | nie jest dowodem integralności ani backupu |
| Zatwierdzony transport SQL | BLOCKED | current/enforced rev5,TCP=[],VPN=false;0SSH | W ustawieniach środowiska Codexa udostępnić wcześniej zatwierdzony TCP ssh.frankfurt.render.com:22 i oficjalną autoryzację; bez nowych kluczy/ról/allowlisty DB; oddzielnie zweryfikować host |
|004/17 i prywatne konta/sesje | BLOCKED | brak potwierdzonych ID i wyników; pakiet4SELECT005 nietknięty | prywatnie zatwierdzić istniejące owner/technical ID; agent wykona tylko4SELECT w jednym READ ONLY REPEATABLE READ; STOP przy innym schemacie; A już jest |
| PITR funkcja / punkt / RPO≤60 | BLOCKED dla skutecznego RPO | dokumentacja płatnegoPG potwierdza funkcję,nie bieżący status recovery; GET nie ma latest point/WAL lag | Render→baza→Recovery: odczytać najnowszy skutecznie odzyskiwalny timestamp/lag i wiek≤3600s; jeśli UI nie pokazuje, uzyskać dowód od Render Support; nie uruchamiaćRestore |
| Aktualna niezależna kopia | BLOCKED | historyczny export1XI starszy niż7dni; brak bieżącego obiektu/manifestu | zatwierdzony magazyn poza aplikacją: potwierdzić aktualny obiekt,czas,hash,region,lifecycle/retencję i dostęp; nowa kopia/usługa/restore wymagają osobnej zgody |
| Odzyskiwalność klucza | BLOCKED | brak dowodu niezależnej wersji klucza i dostępności recovery operatora | zatwierdzony menedżer sekretów: potwierdzić wersję,kontrolę dostępu i odzyskanie; nie przesyłać wartości klucza do rozmowy/repo |
|007 awaryjny odczyt — kod | PASS dla5e4188a | oba pełneCI42713625735/42713880948SUCCESS,394PASS; rzeczywiste sesje/RBAC,SQLSTATE25006 i21fingerprintów bez zmian; pełny build obrazu PASS | ograniczony odczyt,bez nowego loginu/UI; końcowy guardWebSocket wymaga własnegoCI; obraz efemeryczny nie jest zachowany wRender |
| Artefakt rollbacku Render | BLOCKED | live/deactivated deploy nie ujawnia eligibility ani snapshotu env; staryd15265b nie startuje007 | Render→usługa→Deploys: potwierdzić konkretny dostępny digest/obraz,start/env; nie klikaćRollback. Dla nowego profilu potrzebna późniejsza zgoda na budowę/zachowanie artefaktu i akceptacja odczytu zamiast pełnej pracy |
| Handoff i retencja | BLOCKED wykonania | stare procesy nie respektują pauzy; nowe lokalne statusy nie potwierdzają ich wyjścia | zaakceptować plan027 i okno maintenance,udowodnić zakończenie wszystkich starych writerów,uzgodnić kolejkę/retencję oraz dopiero potem osobno zezwolić na resume |
| Gotowość funkcji do testów | PASS syntetyczne wejścia | normalne login/CRM/lejek/wizyty/nativezadania/raporty/PWA w380testach wejścia | produkcyjne logowanie zmienia sesję i wymaga właściciela; obecne flagi/native007/konta niezweryfikowane; żadnego testowego klienta na produkcji |
| Zgoda wydania | BLOCKED | brak zgody na merge/deploy/migrację/aktywację | dopiero po zamknięciu powyższych dowodów zatwierdzić konkretny SHA,schemat,start,okno i rollback; nie traktować tego raportu jako zgody |

RPO pozostaje wymaganiem60min; nie zastąpiono go dzienną kopią ani statusem AVAILABLE.
Nowy tryb awaryjny nie zmienia domyślnej aplikacji, nie leczy starego obrazu i nie
włącza007 na produkcji. PR #6/#8 i automatyzacja Codexa bez zmian/OFF.
Zgoda A nie rozszerza się na zapytania preflight nowego profilu007 ani na jego uruchomienie.

---

# Ai Focus3.0.4 — gotowość produkcyjna, sesje024–025

**Decyzja produkcyjna: BLOCKED.** Zielony kod i testy syntetyczne nie potwierdzają
aktualnej integralności klientów, skutecznego RPO ani możliwości rollbacku w Render.
Wejście80f4652: pełne CI42647145719/42647135285 SUCCESS,359 PASS. Kandydat024180d776 ma pełny CI42653906423 SUCCESS/364 PASS.
Kod025 f5971cf ma pełny CI42657210080 SUCCESS/380 PASS;
backend/build/Chromium/WebKit/audyty PASS,0 znanych podatności. Końcowe dopiski dokumentacyjne
mają własny SHA i wymagają weryfikacji Checks PR #3. Nie jest to zgoda na wydanie. PR #3 Draft, bez zgody na merge/deploy.

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
| Pełny końcowy CI024 | PASS |180d776, workflow42653906423 SUCCESS,364 PASS/130.19s; build/Chromium/WebKit/audyty PASS,0 podatności | brak dla024; kolejne zmiany potrzebują własnego CI | dowód dotyczy kodu/testów, nie produkcji | zachować wymaganie pełnego CI nowego HEAD | nie |

## Uzupełnienie bezpieczeństwa startu —025

| Bramka | Status | Konkretny dowód | Brakujący element | Ryzyko / granica | Następna bezpieczna czynność | Zgoda właściciela |
|---|---|---|---|---|---|---|
| Brak odtworzenia technicznego managera w nowym kodzie | PASS kodu/testów |16 przypadków bootstrapu; legacy sekret ignorowany, konta/hash/sesje bez zmian; dwa starty PG tworzą1 ownera | brak dla kodu025; rzeczywiste konta nadal niezweryfikowane | nie wyłącza aktualnego konta; stary d15265b nadal ma stare zachowanie | CI42657210080 PASS; zachować A dla rzeczywistych kont | kod/testy zatwierdzone; realne konta/config wymagają osobnej zgody |
| Pełny końcowy CI025 | PASS |f5971cf, workflow42657210080 SUCCESS,380 PASS/166.46s; build/Chromium/WebKit/audyty PASS,0 podatności | brak dla testowanego kodu; końcowy dopisek ma własne CI | nie dowodzi gotowości produkcji | potwierdzić Checks dokładnego końcowego HEAD | nie |

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
Render CLI2.33 sprawdzono wyłącznie przez lokalny help: brak komendy recovery/latest point.
Nie logowano się i nie uruchomiono żadnej operacji CLI do produkcji.
Historyczne dowody snapshotu/recovery: session005 i session006, bez ponownego restore.
