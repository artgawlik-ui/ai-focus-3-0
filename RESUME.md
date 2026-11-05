# Wznowienie po sesji 010

[Raport 010](docs/sessions/session-010/REPORT.md). Wydanie nadal BLOCKED.
Sesja 009 zapisana i wysłana: 9858db3177dd003e9463d55ec72eb8fd406287bb.
Sesja 010 dodaje wspólną transakcyjną blokadę kontaktu salonu (PostgreSQL advisory)
w workerze, zapisie opt-out i wiązaniu rozmowy. Bez migracji i zmian flag.
Lokalny PG17: 36 testów PASS, w tym 3 nowe testy integracji/współbieżności;
rozszerzona regresja Meta/inbox/worker/supervisor: 85/85 PASS (zbiory nakładają się).
CI 009 zakończone success: https://github.com/artgawlik-ui/ai-focus-3-0/actions/runs/42081039659.
Kod 010 wysłany jako def70f3; opis PR przez REST zaktualizowany, Draft potwierdzony.
Wynik CI końcowego SHA sprawdzić w Checks PR #3; nie deklarować PASS przed success.
Przy rolling deploy stare procesy nie przestrzegają nowej blokady: wymagane zakończenie
starych workerów przed aktywacją odbioru Meta. Transport DM pozostaje wyłączony.
Brak grantu SSH/aktualnego SQL, dowodu RPO60 i weryfikacji artefaktu rollbacku nadal blokuje wydanie.
Zgoda A aktualna. Następny krok: grant TCP Codex do ssh.frankfurt.render.com:22,
potem weryfikacja hosta/kanału i dokładnie 4 SELECT-y. Bez otwierania allowlisty.
Szacunek nadal 5 sesji podstawowych + ≥1 DM; operacyjne bramki niezamknięte.

---

# Aktualizacja po sesji 009

Raport: [sesja 009](docs/sessions/session-009/REPORT.md). Wydanie nadal **BLOCKED**.
Nowe poprawki workera: awaria opcjonalnego AI zachowuje analizę regułową;
ponowna kontrola dostępu i blokady kontaktu przed zapisem szkicu, odświeżenie ORM
oraz blokady użytkownika/salonu do końca transakcji. Bez zmiany flag i schematu.
Lokalnie 29 testów PASS (17 nowych). CI dokładnego HEAD sprawdzić w PR #3.
Punkt wejściowy: 05a9e6be77b6993d942a9b4cc76398527b403298.
Przy wznowieniu jego CI nadal trwało; backend/build miały success, E2E/audyty oczekiwały.
Nie powtarzać testów bez przyczyny. Zgoda A pozostaje aktualna, TCP nadal puste.
RPO 60 niepotwierdzone. Bez produkcyjnego SQL, deployu, merge i aktywacji Meta.
Szacunek nadal 5 sesji podstawowych + ≥1 DM, zależny od zamknięcia bramek.

---

# AI FOCUS 3.0.4 — punkt wznowienia po sesji 008

**Status wydania: BLOCKED.** Raport: [sesja 008](docs/sessions/session-008/REPORT.md).

Właściciel w poleceniu sesji 008 potwierdził **zgodę A** na dokładnie cztery SELECT-y
przez autoryzowany wewnętrzny kanał READ ONLY oraz **kontrolowany tryb workera**.
Zapis/push tej gałęzi są zatwierdzone. Wcześniejsze ograniczenie wyłącznie lokalnej
pracy oraz historyczne „A nieudzielona” nie opisują aktualnej decyzji. Nie prosić o A ponownie.
RPO=3600 s pozostaje wymagane i niepotwierdzone.

Checkpoint wejściowy 008: **33790a728493e3a19d97fc455b1f76be6d452ce0**;
PR #3 open/Draft, baza d15265b; CI PR 42062017735 success.
W 008 potwierdzono running/connected/current środowiska, ale polityka TCP nadal ma
`domains=[]`, `ip_ranges=[]`, VPN=false. **Brak grantu SSH; 0 prób SSH, 0 SELECT-ów.**
Jedyna bieżąca czynność odblokowująca dostęp: w konfiguracji środowiska Codex zatwierdzić
ograniczony grant TCP do `ssh.frankfurt.render.com:22`. Nie zmieniać allowlisty PostgreSQL.
Po grancie najpierw zweryfikować host key/autoryzację/kanał; nie zakładać ich dostępności.
Identyfikatory kont wymagają prywatnego potwierdzenia; nie zgadywać ich.

Nowa rzeczywista poprawka 008: supervisor obejmuje start dzieci procedurą zamykania,
aby błąd uruchomienia workera nie zostawiał API bez nadzoru. Pięć nowych testów na mockach;
lokalnie 12/12 PASS łącznie z istniejącymi testami gate i offsite. Bez zmiany flag,
poleceń startowych, schematu, semantyki workera lub limitu zamykania 25 s.
Pełna regresja jest sprawdzana w standardowym CI gałęzi; wynik dokładnego końcowego SHA
odczytać w Checks. Nie przypisywać wyniku checkpointu nowemu commitowi.
Nie powtarzano restore eksportu, nie uruchamiano późniejszych nieudanych prób lokalnego startu.

## Następna sesja — bez powtarzania zamkniętych etapów

1. Sprawdzić HEAD/PR/CI ostatniego commita i stan grantu TCP.
2. Bez grantu nie próbować SSH. Po grancie zweryfikować zaufaną tożsamość hosta i kanał READ ONLY;
   potem dokładnie cztery zatwierdzone SELECT-y z sesji 005, bez DML/DDL i danych osobowych.
3. RPO: nadal brak dowodu latest recoverable point ≤60 min i skuteczności tej ścieżki.
   AVAILABLE i snapshot 17/23/004 nie zamykają tej bramki. Restore/testowa recovery DB,
   nowe kopie/eksporty, koszty i zmiany konfiguracji wymagają osobnej zgody.
4. Potwierdzić dostępność artefaktu/env rollbacku i kontrolę zapisów/retencji workera
   przed osobno zatwierdzonym wydaniem. Kontrolowany tryb zaakceptowano, nie wykonano rollout.
5. Bez merge/deploy/restartu/cleanup/migracji produkcji/aktywacji Meta i realnych DM.

Pozostaje szacunkowo **5 sesji podstawowych + ≥1 dotycząca DM**; licznik nie maleje
za poprawkę kodu i dokumentacji przy otwartych bramkach operacyjnych. Nie jest to termin gwarantowany.
SHA aktualizacji: `git log -1 --format=%H -- RESUME.md`. Raport końcowy rozmowy wskazuje
zweryfikowany SHA i CI. Poniżej zachowano historyczne dowody sesji 001–007.

## Źródło prawdy i zapisany commit

- Repozytorium: https://github.com/artgawlik-ui/ai-focus-3-0
- Gałąź: `fix/3.0.4-meta-validation`.
- Draft PR #3: https://github.com/artgawlik-ui/ai-focus-3-0/pull/3 — open, bez merge.
- Ostatni zweryfikowany commit kodu/dokumentacji przed tym punktem wznowienia:
  **19cf9db71474df0588f74cdaa91839c752ee8602**.
- Lokalny HEAD, zdalna gałąź i PR HEAD były zgodne z tym SHA przed zapisem RESUME.md.
- Pierwotny commit dodający RESUME.md: 60644d8bc208f356060b7629273c1412786d14a2.
  Ostatnia aktualizacja tego pliku (może być późniejsza) ma SHA:
  `git log -1 --format=%H -- RESUME.md`; nie wpisujemy rekurencyjnie własnego przyszłego SHA.
  Końcowy SHA checkpointu podano również w raporcie rozmowy i opisie PR.
- Main/baza PR i ostatnia potwierdzona produkcja: d15265b26524d594bdbcb4bc6b63fcbc398a1424,
  wersja 3.0.3, deploy dep-dbjhl6jbc2fs73crj65g. To datowany odczyt, nie gwarancja stanu
  w nowej sesji. Lokalny ref main bywał starszy — porównywać z aktualną bazą PR/origin/main.

Wszystkie zatwierdzone zmiany kodu i dokumentacji sesji 001–006 są już w zdalnej gałęzi
oraz PR. Żadnych zmian aplikacji/stanu produkcji nie wprowadzono w tym checkpoincie.
Nieśledzone lokalne archiwa reports/ai-focus-3-audit.zip, ai-focus-3-meta-audit.zip,
ai-focus-3-phase-1-2.zip nie są nowymi zmianami kodu/dokumentacji; nie otwierano ich
ani nie publikowano. Mogą zawierać dane prywatne. Nie są wymagane do odtworzenia kodu.
`.render-auth`, klucze, cookies, kopie i dumpy nie są częścią repo. Nie zakładać ich trwałości
ani dostępności po przerwie; używać oficjalnej autoryzacji usług, nigdy sekretów w rozmowie.

## Wyniki CI — przypisane do konkretnego SHA

Dla **19cf9db** ponownie odczytano success obu uruchomień:
- PR: https://github.com/artgawlik-ui/ai-focus-3-0/actions/runs/41361537654
- push: https://github.com/artgawlik-ui/ai-focus-3-0/actions/runs/41361532882
- **143 testy PASS**, build frontendu PASS, Chromium desktop PASS,
  WebKit z emulacją iPhone'a PASS; pip-audit/npm audit: 0 znanych podatności.
- 11 testów operatorskiego cleanup celowo wykluczonych z kolekcji, zgodnie z zakazem;
  nie przedstawiać ich jako wykonanych. Regresja krytycznych funkcji aplikacji pozostała.
  Procentowego code coverage nie mierzono. Lista i wyjaśnienie: session-004/FINAL_REVIEW.md.
- Prawdziwą instalację PWA i logowanie na fizycznym iPhonie wcześniej potwierdził właściciel,
  nie Codex. Test WebKit nie jest testem fizycznego urządzenia ani realnego OAuth Meta.

Nowy checkpoint może wywołać oddzielne CI. W nowej sesji odczytać checks jego dokładnego
SHA; nie przepisywać wyniku 19cf9db jako wyniku innego commita. Nie powtarzać lokalnie
niezmienionych pełnych testów/restore bez nowej przyczyny, regresji lub zmiany kodu.

## Obowiązujące decyzje właściciela

1. **RPO = 60 minut / 3600 s**, zatwierdzone 2 listopada. Polityka i gate:
   docs/sessions/session-006/rpo-policy.json oraz docs/meta/3.0.4/RELEASE_GATE.md.
2. Rutynowy kod/testy/dokumentacja wyłącznie na gałęzi roboczej są autoryzowane.
   Nie pytać ponownie o oczywiste kroki w tym zakresie.
3. Historycznie zatwierdzono bazowy koszt Render około 13 USD/mies.; to nie jest zgoda
   na nowy zasób, recovery DB, PITR, nowy magazyn, zmianę planu lub dodatkowe opłaty.
4. Kwota około 0,20 USD compute/24h testowej recovery DB była **wyłącznie propozycją**.
   **Nie zatwierdzono jej utworzenia/testu/usunięcia** ani innych płatnych operacji.
5. Meta działa tylko jako przygotowany kod/mocks; rzeczywista komunikacja wymaga osobnych
   zgód. Każda wiadomość i wizyta wymaga akceptacji. Nie wysyłać testowych DM.
6. Wcześniej zatwierdzono parametry inboxa: done payload 7 dni, metadata 90 dni;
   alert pending ≥100, najstarszy pending >5 min lub dead-letter ≥1;
   przetwarzanie w istniejącym procesie, bez nowego workera/usługi.
   Nie mylić tego z zatwierdzeniem backup retention/nowego magazynu.

## Co zakończono — nie powtarzać bez powodu

- Kod CRM i przygotowanie Meta na aktualnej gałęzi; schema/model zgodne z bazą PR,
  jedyny Alembic head **004**, bez nowych migracji w sesjach 001–006.
- Syntetyczne testy migracji/odtwarzania 17 tabel, sesji i RBAC, CRM, agenta, Meta
  (mocki), inboxa/deduplikacji/lease/retencji/opt-out, szyfrowania i braku DM.
- Bezpieczne preflighty: scripts/readonly_preflight.py, scripts/release_selects.py;
  SQL bez danych/sekretów: docs/sessions/session-005/SELECTS.sql i SELECTS.psql.
  Wariant .sql ma parametry psycopg, .psql prywatne prompt-y psql; nie mieszać formatów.
- **OWNER_VERIFIED:** rzeczywisty eksport z 1 listopada odtworzony lokalnie na PG17.11:
  17 tabel, 23 rekordy, Alembic 004. Samo potwierdzenie nie zawierało SHA/ID pliku.
- **Niezależnie zweryfikowany eksport:** etykieta 2026-11-01 18:25 UTC / 19:25 Warszawa,
  TOC 18:27:29 UTC, 8 996 B, SHA-256
  c7fcd97d374cd3d3696b9ea35a1a99dc83a944e460c890131ad5966d97232a8c.
  Restore do nowego lokalnego kontenera bez sieci/aplikacji/Meta: 17 tabel/23 rekordy/004,
  hash/count i schemat zgodne. Oryginał niezmieniony; kontener/jawne pliki usunięto.
  Nie odtwarzać ponownie tego samego SHA tylko w celu uzyskania kolejnego PASS.
- Reporty sesji 001–006, runbook dostępu, osobne decyzje A/B/C (READ ONLY, cleanup,
  merge/deploy) oraz plan rolling deploy/STOP/recovery. To plany, nie wykonane zgody.

## Aktualne blokady — nie deklarować READY

### A. RPO 60 — niepotwierdzone operacyjnie

Płatny compute PostgreSQL 0.1c-256mb, 1 GB, PG17, Frankfurt; obsługuje PITR.
W sesji 006 API zwracało AVAILABLE i startsAt=2026-10-29T06:32:47Z, bez endsAt/najnowszego punktu/lag WAL. Nowszy odczyt sesji 007 znajduje się na początku tego pliku.
Dokumentacja zabrania punktu z ostatnich 10 min; to nie SLA maksymalnego lag 10 min.
Hobby ma okno 3 dni, Pro+ 7 dni; rzeczywisty workspace billing tier nie jest potwierdzony.
Większa retencja/compute sama nie dowodzi RPO. Nie kupować upgrade jako domyślnego rozwiązania.

Przy odczycie w sesji 006 ostatni eksport miał 17 278 s (4h47m58s), więc sam nie spełniał
60 min. Wiek pobrania/restore nie odświeża punktu źródłowego. Trzeba nowego odczytu,
nie zakładać, że ta liczba lub lista eksportów nadal są aktualne po przerwie.
Brakuje najnowszego skutecznego punktu, testu ścieżki PITR w RPO, nadzoru świeżości
oraz uzgodnionego zakresu awarii (w tym niezależnej ścieżki przy utracie Render).

### B. Dostęp SQL / konta / bieżąca integralność

Hosted Render MCP query jest blokowany przez pustą publiczną allowlistę. Ostatnia polityka
środowiska miała puste granty TCP i VPN=false. Nie otwierać bazy ani nie obchodzić proxy.
Autoryzacja API działała — problemem był kanał SQL, nie konieczność nowego hasła/tokenu.
Potrzebny zatwierdzony wewnętrzny Shell/SSH istniejącej usługi i ograniczony grant wykonawcy,
prywatnie zatwierdzone ID właściciela/technicznego konta. Nie używać historycznych cookies CRM.
Brak świeżego potwierdzenia 004/kont/sesji/hashów. Snapshot 17/23/004 nie jest bieżącą produkcją.

### C. Trwały szyfrowany magazyn i klucz

Nie potwierdzono niezależnego trwałego magazynu/klucza/retencji. OFFSITE_BACKUP_ENABLED było OFF.
Kod offsite jest dzienny, retry po błędzie 1h; backup trzyma SHARE LOCK i dump w RAM.
Samo włączenie lub interwał godzinny nie realizują RPO 60. Proponowana retencja 30 dni
wymaga osobnej akceptacji. Nie uruchamiać nowego eksportu/backup scheduler bez zgody.

### D. Worker / rollout / rollback

AGENT_V2_ENABLED było już ON; **ON/OFF nie zatrzymują workera**. Może zapisywać zadania,
szkice/Activity i wykonywać retencję także przy Meta OFF. Nie wysyła DM ani sam nie tworzy wizyt.
W rolling deploy mogą współistnieć stare/nowe procesy. Wymagane uzgodnione okno bez zapisów
albo rozliczenie każdej zmiany count/SHA, bez pomijania całych tabel w celu wymuszenia PASS.
Ostatni punkt powrotu live: d15265b/dep-dbjhl6jbc2fs73crj65g. API nie potwierdza eligibility
zachowanego obrazu. Przed wydaniem sprawdzić artefakt i env target deployu.
Start.sh uruchamia alembic upgrade head i worker — nie używać go do odczytowego preflightu.

### E. Meta i zgody operacyjne

Zapisana konfiguracja Meta/DM była OFF, env groups 0, paid AI OFF; to datowane metadata,
nie snapshot env działającego procesu ani targetu rollbacku. Nie aktywować integracji.
Development OAuth i Live webhook to oddzielne bramki; dokumentacja wymaga Live do
notifications app users. Nie przełączać trybu i nie wnioskować o Advanced Access bez zgody.
Nie udzielono zgody na merge/deploy/produkcję, cleanup, zmiany sieci/uprawnień/sekretów,
restarty, produkcyjne migracje, nowy eksport, PITR, płatne zasoby i realne DM.

## Sesja 007 — dokładna instrukcja wznowienia

1. Przeczytaj RESUME.md i najnowsze polecenie właściciela oraz aktualny PR #3.
   Sprawdź AGENTS.md, lokalny status, gałąź, HEAD zdalny/PR i checks dokładnego SHA.
   Nie resetuj nowych zmian ani nie nadpisuj pracy innej sesji. Nie myl starego ref main z bazą PR.
2. Przeczytaj aktualne instrukcje środowiska/usług; użyj oficjalnej autoryzacji i sprawdź
   workspace My Workspace. Odczyt Render i metadata był dozwolony; mutacje poniżej nie są.
   Jeżeli nowa sesja nie ma dostępu, zdiagnozuj plugin/CLI przed prośbą o oficjalną autoryzację.
3. W dozwolonym zakresie tylko GET: odśwież recovery/eksporty/plan i policz wiek punktu
   źródłowego względem 3600 s. Spróbuj ustalić latest recoverable point, ale AVAILABLE/startsAt
   nie zastępują dowodu. Nie twórz eksportu, recovery DB ani płatnego testu.
4. Przedstaw najprostszy brakujący krok właściciela: zatwierdzony kanał READ ONLY i/lub
   potwierdzenie latest point przez Recovery/support. Nie wysyłaj wiadomości do supportu samodzielnie.
5. Dopiero po osobnej zgodzie: zaplanowany jednorazowy PITR do izolowanej nowej DB,
   nigdy nadpisanie/zmiana połączeń produkcji. Muszą być zatwierdzone koszt, czas i zakończenie
   testu oraz kanał read-only do nowej DB. Szacunek tej samej 0.1c/256 MB, 1 GB: ok. 0,20 USD
   compute/24h przy 30-dniowym miesiącu, lecz cenę trzeba odczytać ponownie przed zgodą.
6. Bez nowych zgód kontynuuj wyłącznie niezależne lokalne przygotowania/dokumentację,
   nie powtarzaj zakończonych etapów. Nie nazywaj BLOCKED „READY” na podstawie samych testów kodu.
7. Zapisz docs/sessions/session-007/REPORT.md, z rzeczywistymi dowodami i stanem blokad,
   aktualizuj tę samą gałąź/Draft PR bez merge. Testy PostgreSQL tylko sekwencyjnie.

**Stałe ograniczenia:** nie modyfikuj Focus 1.0/2.0, danych klientów, konfiguracji Render/Meta,
sekretów/uprawnień/sieci. Bez DELETE/cleanup, produkcyjnych migracji, restartów, merge/deploy,
nowego eksportu, zakupu zasobów i aktywacji Instagrama bez osobnej zgody. Bez realnych DM.
Nie proś o hasła/tokeny/klucze w czacie; wartości wyłącznie przez zatwierdzony magazyn.
Nie uruchamiaj skryptów z .tools tylko dlatego, że istnieją — część jest historyczna i produkcyjna.

## Najważniejsze pliki

- docs/sessions/session-006/REPORT.md — RPO/plan/źródła/koszty i aktualne kryteria.
- docs/sessions/session-006/RECOVERY_PROCEDURE.md — szyfrowanie/klucze/restore i wariant PITR.
- docs/sessions/session-005/REPORT.md, RELEASE_PLAN.md — snapshot/worker/SELECT/STOP.
- docs/sessions/session-004/FINAL_REVIEW.md — semantyka agenta, wyłączone testy i bezpieczeństwo dowodów.
- docs/sessions/session-003/ACCESS_RUNBOOK.md, DECISIONS.md — dostęp i rozdzielone zgody A/B/C.
- docs/meta/3.0.4/RELEASE_GATE.md — bieżący gate BLOCKED; historyczne READY poniżej nie unieważnia RPO.

Pozostaje szacunkowo **5 sesji podstawowych + co najmniej 1 DM**. Nie zmniejszać licznika
za samo przygotowanie, dopóki krytyczna bramka operacyjna nie zostanie zamknięta.
Ten dokument nie uruchamia pracy w tle, sesji 007 ani GitHub automatyzacji wdrożenia.

## Jedno polecenie dla nowej sesji Codexa

> Wznów sesję 007 Ai Focus 3.0.4 w repozytorium artgawlik-ui/ai-focus-3-0, gałąź fix/3.0.4-meta-validation, PR #3: najpierw przeczytaj RESUME.md z aktualnego HEAD, sprawdź stan gałęzi i CI, a następnie wykonuj plan sesji 007 bez powtarzania zakończonych etapów i z zachowaniem wszystkich zapisanych ograniczeń; RPO=60 minut, status wydania BLOCKED, bez merge/deploy/cleanup/restore/nowego eksportu/zmian produkcji/płatnych zasobów i aktywacji Meta bez nowej osobnej zgody.
