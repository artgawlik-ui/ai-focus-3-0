# Issue #4 — decyzja release gate

> Sesja 008: zgoda A i kontrolowany tryb workera **zatwierdzone przez właściciela**.
> Kanał SQL nadal BLOCKED (puste granty TCP); 0 zapytań. RPO 60 niepotwierdzone.
> Poprawka supervisora przetestowana lokalnie na mockach; brak deployu i zmian produkcji.
> [Raport 008](../../sessions/session-008/REPORT.md). Historyczne zapisy o braku A nie są aktualne.

> Aktualizacja 2026-11-02 (sesja 006): właściciel zatwierdził **RPO = 60 minut**.
> Bieżący gate wydania: **BLOCKED**. PITR AVAILABLE nie dowodzi latest recoverable point
> ≤60 min; ostatni eksport jest starszy niż limit. Historyczne READY poniżej dotyczyło
> wąskiego kandydata kodu, nie zamkniętego recovery. Obowiązuje [raport sesji 006](../../sessions/session-006/REPORT.md)
> i [procedura RPO/kluczy/restore](../../sessions/session-006/RECOVERY_PROCEDURE.md).


Ten dokument aktualizuje stan raportu issue #2, nie usuwa jego historycznych dowodów.

| Zakres | Decyzja |
|---|---|
| **Kod 3.0.4 z wyłączoną Meta, do osobnego zatwierdzenia wydania** | **READY** po zielonym CI tej gałęzi. Nie oznacza zgody ani wykonania merge/deploy. |
| **Aktywacja Meta (OAuth, webhook, ingest, CRM history, diagnostics, DM)** | **BLOCKED**. Nic nie zostało aktywowane. |
| Bieżący wewnętrzny odczyt SQL produkcji | **BLOCKED**, brak dostępnego bezpiecznego kanału. |
| Rzeczywisty PITR / pełne granice czasu / produkcyjne RPO i RTO | **BLOCKED / nieprzetestowane**, nie uruchamiano płatnego restore. |

## Dlaczego kod jest gotowy do decyzji właściciela

Issue #4 wymaga porównania odtworzenia z punktem eksportu, a nie z późniejszą zmieniającą się bazą. Ten gate został wykonany: [BACKUP_VERIFICATION.md](BACKUP_VERIFICATION.md), [provenance](issue4-evidence/export-provenance.json), [restore](issue4-evidence/restore-verification.json).

- Świeży wskazany przez właściciela eksport faktycznie pobrany, gzip/tar/TOC/CRC/rozmiar/SHA-256 sprawdzone; 17/17 liczności i fingerprintów źródłowego COPY zgodnych z odtworzeniem.
- Schemat eksportu **004** kompatybilny z niezmienionymi modelami 3.0.3/3.0.4; brak nowych migracji. 127 kolumn, 40 ograniczeń, 34 indeksy łącznie. Właściciel aktywny, konto techniczne wyłączone i bez ważnych sesji — **na punkt eksportu**.
- **105/105** testy lokalne, 0 failed/errors/skipped; wcześniej 90/90. Nowe testy obejmują integralność archiwum, ścieżki, linki, limity, format COPY i odmowę pracy w produkcji lub z błędnym hashem. Regresja CRM/Meta/bezpieczeństwa i migracji pozostaje zielona. Końcowy GitHub CI jest warunkiem użycia statusu READY; wynik widoczny w PR #3.
- Backend, frontend i schemat produkcyjny nie są przebudowywane. Nowe pliki issue #4 to narzędzia testowe i dokumentacja; nie wywołują się automatycznie w aplikacji. Dotychczasowe poprawki 3.0.4 pozostają za wyłączonymi modułami, a blokada DM jest wewnętrzna i niezależna.
- Odczyt Render potwierdził live **3.0.3 / d15265b26524d594bdbcb4bc6b63fcbc398a1424**, deploy **dep-dbjhl6jbc2fs73crj65g**. Publiczny test HTTPS i nagłówków PASS, prywatne API bez sesji 401, GET OAuth/webhook 404. Grupy środowiska workspace: 0. Autodeploy był wyłączony; brak deployu tej gałęzi.

**READY ma wąski zakres:** kandydat kodu bez zmiany schematu i z Meta OFF może zostać przedstawiony właścicielowi do decyzji. Nie deklarujemy pełnej walidacji bieżącej bazy, pracy rzeczywistego Instagrama ani pełnej gotowości operacyjnej recovery. Nie porównujemy dumpa do aktualnych rekordów i nie twierdzimy, że po eksporcie nie pojawiły się nowe dane. Przed faktycznym wydaniem należy ponownie sprawdzić commit/efektywne flagi oraz aktualność punktu odzyskiwania; zmiana tych założeń wymaga ponownej oceny gate.

## Każda flaga osobno — odczyt, bez zmian

Źródło: [configuration-status.json](issue4-evidence/configuration-status.json) oraz brak env groups w [render-release-readonly.json](issue4-evidence/render-release-readonly.json).

| Flaga | Stan na odczyt API | Efektywne zachowanie kodu |
|---|---|---|
| META_ENABLED | ustawiona, false | legacy OFF |
| META_OAUTH_ENABLED | pusta / brak | dziedziczy false |
| META_WEBHOOK_VERIFY_ENABLED | pusta / brak | dziedziczy false |
| META_INGEST_ENABLED | pusta / brak | dziedziczy false |
| META_CRM_HISTORY_ENABLED | pusta / brak | dziedziczy false |
| META_DIAGNOSTICS_ENABLED | pusta / brak | dziedziczy false |
| META_DM_TRANSPORT_ENABLED | pusta / brak | niezależnie false, fail-closed |

META_MODE to development, nie przełącznik wysyłki. Nie zmieniono żadnej flagi. Nawet hipotetyczne true flagi transportu daje 501, bez HTTP. Podpisane callbacki prywatności mają osobną dotychczasową semantykę; ich dostępności nie oznaczamy jako uruchomienia ingestu. Nie wywoływano ich na produkcji.

## Dlaczego Meta pozostaje BLOCKED

- Puste META_APP_ID, META_APP_SECRET, META_VERIFY_TOKEN, META_ENCRYPTION_KEY i META_TEST_ACCOUNT_ID. CONFIG_ID i dokładny redirect są ustawione. Nie potwierdzono w Meta powiązania configuration ID z aplikacją, uprawnień ani zatwierdzonego IG user ID.
- Brak autoryzacji prawdziwego konta i dozwolonego testu integracji. Dotychczas wszystkie funkcjonalne testy są mockami/fixture'ami. Nie wolno przedstawiać ich jako rzeczywistych testów Instagrama.
- Stan credential/inbox/refresh pusty **w eksporcie**; nie jest to aktualny odczyt produkcji. Przed ustawieniem/odtwarzaniem klucza Fernet potrzebna bieżąca kontrola stanu, bez rotacji istniejącego klucza.
- Retencja failed/dead-letter i podstawa prawna wymagają uzgodnienia. Usuwanie treści w inboxie/wiadomościach i trwała rezygnacja są przetestowane; dawne backupy mogą nadal zawierać usunięte treści, więc recovery musi respektować rejestr usunięć.
- Pełna operacyjna weryfikacja aktualnej bazy i recovery pozostaje otwarta. Automatyczny aplikacyjny offsite jest wyłączony, klucz i pola S3 puste; nie oznacza to wyłączenia osobnego PITR Render.

## Bezpieczny wewnętrzny odczyt — plan i blokada

Nie otwierać IP allowlist, nie wystawiać bazy publicznie. Aktualny hosted MCP jest przez pustą allowlistę blokowany. Środowisko wykonawcze nie ma grantów TCP; próba SSH z prawidłową lokalną konfiguracją kończy się connection refused. Nie zmieniano tego stanu.

Docelowo agent korzysta z zatwierdzonego SSH/Shell **istniejącej usługi ai-focus-3-0**, wewnętrznego DATABASE_URL i transakcji **REPEATABLE READ READ ONLY**, z krótkim statement_timeout. Wykonuje [READONLY-SQL.sql](READONLY-SQL.sql) i zwraca wyłącznie agregaty/hashe; nie startuje aplikacji, bootstrapu, workerów, migracji ani backupu blokującego zapisy. Nie udostępnia endpointu SQL ani sekretów w WWW. Harmonogramy pozostają nietknięte.

Jeżeli agent nie ma takiego kanału, kontrola pozostaje BLOCKED. Konkretna czynność właściciela przed jej wznowieniem: zatwierdzić dostęp SSH istniejącej usługi przez oficjalne **Render Account Settings → SSH Keys**, wraz z osobno zatwierdzonym, ograniczonym grantem TCP środowiska Codex do `ssh.frankfurt.render.com:22`. Nie przesyłać prywatnego klucza ani tokenu w rozmowie. Samo dodanie klucza bez grantu TCP nie usunie blokady; nie wykonywano żadnej z tych zmian. Alternatywny wewnętrzny kanał należy zatwierdzić i sprawdzić przed użyciem, nie tworzyć płatnego joba/instancji jako obejścia.

## PITR: co odblokowano, co pozostało

API potwierdza **AVAILABLE** i **startsAt 2026-10-29T06:32:47Z**, co usuwa wcześniejszy brak potwierdzenia dolnej granicy. Nie zwraca górnej granicy; screenshot kalendarza i reguła „nie ostatnie 10 minut” nie dowodzą pełnego okna 72 h. Nie wykonano PITR. Dokładny następny krok panelowy bez zmiany zasobów: **ai-focus-3-0-db → Recovery → Point-in-Time Recovery → otworzyć formularz i odczytać dostępne daty/godziny; nie klikać Start Recovery**. Samo otwarcie formularza nie stanowi testu.

Płatna próba wymaga osobnej zgody po przedstawieniu aktualnej ceny nowej instancji i planu usunięcia/cutover. Nie wyceniono ani nie uruchomiono jej w tym zadaniu. Dodatkowe płatne zasoby i dodatkowy compute Render w tym zadaniu: **0**. Bieżącego rachunku całego workspace nie audytowano.

## Rollback i decyzje właściciela

1. **Merge/deploy:** wymagają osobnego pisemnego zatwierdzenia. PR #3 pozostaje Draft, issue #4 otwarte. Nie włączać automerge ani automatycznego deploy.
2. **Przed zatwierdzonym deployem:** utrzymać jawnie wszystkie moduły Meta i DM OFF, zapisać aktualny deploy/commit i aktualny punkt odzyskiwania; ocenić zmiany danych po eksporcie. Jeśli aktualna produkcja/konfiguracja odbiega od zweryfikowanego baseline, wstrzymać wydanie.
3. **Cel kodowy rollbacku:** d15265b / dep-dbjhl6jbc2fs73crj65g. Jest live i źródło jest dostępne. API nie dowodzi przyszłej retencji obrazu po nowym deployu: sprawdzić dostępność Rollback w Render przed użyciem; awaryjnie zatwierdzony rebuild tego commita. Żadnego triggera nie wywołano.
4. **Dane:** brak nowej migracji; nie wykonywać DROP/downgrade ani overwrite. 004 i inbox zostają. Celowo usunięte treści nie powinny wracać po cofnięciu kodu ani po recovery. Powrót kodu nie jest odzyskaniem bazy.
5. **Po rollbacku:** sprawdzić commit/health/efektywne flagi (zmienne target deploy i env groups mogą się różnić), a nie zakładać ich stanu. Całość zgodna z [ROLLBACK.md](ROLLBACK.md).
6. **Meta:** wymaga odrębnej decyzji po konfiguracji, rolach i kontrolowanym teście; transport DM nadal poza zakresem i wyłączony. Żadnych rzeczywistych DM także podczas testów.

Lokalne narzędzia i raport nie zmieniają Focus 1.0/2.0, produkcyjnych danych, sekretów, sieci ani ustawień. Nie utworzono nowego płatnego serwisu, recovery instance, workera ani kolejki.
