# Ai Focus 3.0.3 — raport poprawki Meta (2026-11-01)

**Status: przygotowane i testowane lokalnie, niewdrożone.** Wyłącznie gałąź `fix/3.0.3-meta-instagram-unified-login`, z main `ba951fd43a0ef5d81e61457f7a541300e9b3b336`. Nie zmieniano produkcyjnego Render, zmiennych, bazy ani kluczy. Nie wykonywano rzeczywistych żądań Graph/Instagram API, wysyłki DM, aktywacji ani zmian Focus 1.0/2.0. Domena istniejącej aplikacji: https://ai-focus-3-0.onrender.com — ta poprawka jeszcze tam nie działa. Nie deklarujemy gotowości produkcyjnej ani autoryzacji prawdziwego konta.

## 1. Zmiany i działanie

- OAuth: usunięta blokada nazwy `artur_uluru_hair`, nadal wymagane zgodne IG user ID z `META_TEST_ACCOUNT_ID`, uprawnienia tokenu, aplikacja, właściciel manager+email, aktywna sesja, nonce/state i jednorazowy kod. Dodano porównanie cookie bieżącej sesji z sesją inicjującą OAuth. `#_` usuwane raz. Żadne poświadczenie nie trafia do odpowiedzi API.
- Oddzielne flagi modułów i niezależna blokada DM w samej funkcji `send_dm`. **Nawet true kończy się 501**: poprawka nie implementuje wysyłki. Nie ma trasy /send; zatwierdzenie szkicu i manual_sent nie wykonują HTTP.
- Webhook: surowe body -> stałoczasowa weryfikacja podpisu -> szyfrowany inbox PostgreSQL -> commit -> 200. Brak pracy CRM i HTTP do dostawcy w ścieżce odpowiedzi. Błąd zapisu daje 503, przekroczenie limitu 413. Zdarzenia nieprawidłowe/nieobsługiwane nie tworzą fikcyjnej historii.
- Unikalny SHA-256 tożsamości konto+rodzaj+mid (lub hash treści), `INSERT ... ON CONFLICT DO NOTHING`; osobne klucze usunięcia i echo. Processor używa `FOR UPDATE SKIP LOCKED`, dzierżawy i tokenu fencing. CRM + status done commitują razem. Restart odzyskuje processing; pięć prób, backoff, dead-letter.
- Cykl w istniejącym procesie agenta, bez dodatkowej usługi, kolejki czy nowego wątku przetwarzania. Standardowa pula HTTP obsługuje wyłącznie ograniczony zapis SQL. Błąd integracji nie zatrzymuje kolejki CRM.
- `/refresh` i maintenance: jedna dzierżawa/konto; HTTP poza transakcją i blokadą credential. Timeout, sieć, 5xx, 400/401 czy zły scope zachowują token. Trwałe unieważnienie automatyczne **wyłącznie po debug_token is_valid=false**. Trzy próby, backoff 5/10 s i 24 h cooldown po wyczerpaniu; retry realizuje istniejący agent. Wynik starego sprawdzenia nie może skasować nowego tokenu po OAuth. Jawne disconnect/deauthorize nadal unieważniają poświadczenie na żądanie właściciela/platformy.
- Fernet i envelope `{kind,value}` niezmienione, istniejące tokeny kompatybilne, bez rotacji. Podpisane żądanie usunięcia czyści również zaległe payloady inboxa, aby nie odtworzyć usuniętej treści.
- Owner-only diagnostyka: liczba i wiek najstarszego pending/failed, dead-letter oraz bezpieczny stan kontroli tokenu. Panel pokazuje alert inboxa; handlowiec nadal widzi wyłącznie przydzielone rozmowy.
- Retencja zakończonych zdarzeń: payload 7 dni, metadane 90 dni. Pending/failed/dead-letter nie kasowane automatycznie; wymagają przeglądu i osobnej decyzji o retencji. Alert: pending >=100, pending >300 s lub dowolny dead-letter; log agregatów najwyżej raz/minutę, bez treści/identyfikatorów.

Pełny inwentarz flag, migracja konfiguracji, wymagania sekretów i dokładne URL-e: [ENVIRONMENT.md](ENVIRONMENT.md). Krok 0, przepływ bazowy i decyzje: [PLAN.md](PLAN.md).

## 2. Dokumentacja Meta v26.0 — fakty i ograniczenia

Sprawdzono 2026-11-01, trzy odpowiedzi HTTP 200; daty i SHA-256 źródeł w [DOCUMENTATION-EVIDENCE.json](DOCUMENTATION-EVIDENCE.json).

1. https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-unified-login/get-started — potwierdzono **Unified Login**, Meta App ID/App Secret zamiast Instagram App ID/Secret, `config_id`, wymianę kodu **GET /v26.0/oauth/access_token** z `client_secret` i `code` w query, Business Integration System User token oraz `/me/assigned_instagram_accounts`. Minimalne wymagane scope: instagram_basic i instagram_manage_messages. Domyślna konfiguracja Meta może zawierać też publikację/komentarze/reklamy; kod odrzuca nadmiarowe scope. Właściciel musi ograniczyć konfigurację, nie rozszerzono uprawnień w kodzie.
2. https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-unified-login/authentication — potwierdzono osobną ścieżkę Unified Login; nie stosujemy cyklu ig_refresh_token z Instagram Login. `/refresh` jest kontrolą ważności SUAT, nie obietnicą automatycznego wydłużenia tokenu. Ponowny OAuth przed wygaśnięciem.
3. https://developers.facebook.com/docs/graph-api/reference/debug_token/ — potwierdzono przykład **GET /v26.0/debug_token?input_token=...** i pole is_valid. Nie znaleziono potwierdzenia POST body dla tych dwóch operacji. Zachowano istniejące GET i sposób przekazywania parametrów; nie wykonano nieudokumentowanej zmiany protokołu.

**Ryzyko rezydualne:** oficjalne GET wymagają wartości w URL żądania serwer–Meta. Nie są one zwracane klientowi. Logi wire httpx/httpcore są wyciszone filtrem; obsługa błędów używa stałych komunikatów i kategorii, bez exception repr/traceback/request URL. Uvicorn ma istniejące `--no-access-log`, audyt nie zapisuje query. Jeśli właściciel doda APM/proxy rejestrujące wychodzące URL lub callback query, musi zastosować redakcję przed uruchomieniem. Nie możemy twierdzić, że żadne zewnętrzne narzędzie monitoringu nie zachowa URL — paneli nie zmieniano.

Nie potwierdzono w panelu: przypisania Configuration ID do właściwej aplikacji, rzeczywistych ról/testerów, IG user ID i scopes/token type, App Review/Advanced Access/business verification. Nie przełączano live. Brak prawa do pierwszego DM do dowolnego salonu; okno 24 h w CRM pozostaje informacją, **nie zgodą na wysyłkę**. Webhook nie generuje odpowiedzi.

## 3. Testy i dowody

Wszystkie zapisy na syntetycznych lokalnych bazach PostgreSQL 17. Żadna kopia ani baza produkcyjna nie była używana do zapisu. Zmienne połączenia pominięto w poleceniach poniżej.

| Sprawdzenie | Polecenie | Wynik |
|---|---|---|
| Bazowy backend | `.venv/bin/python -m pytest -q --tb=no --show-capture=no` | 49 passed, 0 failed/errors/skipped |
| Poprawka, pełny backend/security/concurrency/migration | `PYTHONPATH=/tmp/focus3-readonly-audit:. .venv/bin/python -m pytest -p network_guard -q --tb=no --show-capture=no` | **80 passed, 0 failed/errors/skipped**; RESULTS.json i evidence/backend-junit.xml |
| Frontend | `npm run build --prefix frontend` | TypeScript + Vite PASS, 1579 modułów |
| E2E | `PYTHONPATH=/tmp/focus3-readonly-audit:. PLAYWRIGHT_BROWSERS_PATH=/tmp/focus3-browsers .venv/bin/python -m tests.ci_e2e` | Chromium desktop PASS, WebKit iPhone 13 PASS |
| Audyt frontend | `npm audit --prefix frontend --json` | 0 podatności wszystkich poziomów |
| Audyt backend | `.venv/bin/pip-audit -r requirements.txt --format=json` | 0 znanych podatności |
| Zasoby | `.venv/bin/python -m tests.meta_resource_probe` | 20/20 inbox done, szczegóły niżej |
| Whitespace | `git diff --check` | PASS |

Pierwszy bazowy start przy wyłączonym lokalnym PostgreSQL: 10 passed/39 errors; po uruchomieniu istniejącego kontenera 49/49. Pierwszy pip-audit nie miał zapisu do cache środowiska; ponowiono z cache /tmp, audyt zakończony. W końcowym pytest pozostają ostrzeżenia deprecacji pytest/anyio oraz Starlette TestClient/httpx; brak zmiany zależności w tym zadaniu.

Nowe testy: brak/empty/błędna flaga DM + wszystkie inne true i mock odrzucający wysyłkę; autoryzowany target vs błędne konto/właściciel; nonce/state/replay/logout; identyczny redirect; brak sekretów w logach/odpowiedziach; HMAC na dokładnych bajtach i limity; trwały commit przed ack; dwa jednoczesne webhooki z tym samym mid; dwa konsumery, SKIP LOCKED, restart i stary fencing token; rollback pracy CRM przy awarii, retry/dead-letter; retencja i owner-only diagnostyka; timeout/network/5xx/HTTP OAuth/scope bez utraty tokenu; single-flight /refresh, brak blokady credential podczas HTTP, odzyskanie po restarcie, ochrona nowego ciphertext przed starym is_valid=false.

Test migracji tworzy osobną bazę: upgrade do 003 -> dane syntetyczne -> fingerprint wszystkich 14 istniejących tabel danych (bez alembic_version) -> 004 dwa razy -> downgrade do 003 zachowujący dane -> ponowny upgrade -> porównanie liczności i SHA-256 -> `alembic check`. Zachowano istniejące rekordy i oczekujący inbox. Migracja addytywna: dwie tabele; nie zmienia istniejących kolumn ani ciphertext.

E2E: login/logout, CRM read/write, agent szkicowy, historia/szkic/akceptacja Instagram bez wysyłki, manifest/ikony, brak poziomego przewijania, offline i brak prywatnych danych w SW cache. **Emulacja WebKit, nie fizyczny iPhone**; offline WebKit przez lokalny proxy z przerwanym połączeniem. Ręczne potwierdzenie instalacji PWA na fizycznym iPhonie z wcześniejszej fazy pochodzi od właściciela, nie od Codex i nie dotyczy tej gałęzi.

## 4. Render Starter — budżet i ograniczenia

Bez nowej usługi/instancji/Redis/workerów. API i istniejący agent pozostają dotychczasowymi procesami supervisora.

| Limit w kodzie | Wartość / cel |
|---|---|
| PostgreSQL pool | 2 połączenia/proces, overflow 0, pool timeout 5 s; API+agent maks. 4, poza istniejącą osobną procedurą backupu |
| Webhook | body 64 KiB, do 50 zdarzeń/request, jeden batch INSERT i commit; maks. 4 równoległe zadania SQL na istniejącej puli HTTP |
| SQL inbox | lock_timeout 500 ms, statement_timeout 2000 ms; przeciążenie daje 503 i ponowienie dostawcy |
| Procesor | batch 4, pętla co 2 s, bez nowego wątku; lease 120 s, max 5 prób, backoff 5–300 s |
| Refresh | 1 request/konto naraz, lease 90 s, timeout HTTP 10 s/etap, 3 próby; bez aktywnego oczekiwania podczas backoff |
| Monitoring/retencja | co 60 s, bez ponownego zapisu już wyczyszczonych payloadów; ostrzeżenia najwyżej raz/minutę |

Pomiar lokalny: supervisor+API+agent, dwa równoległe logowania, 20 webhooków: **359,45 MiB peak RSS**, maks. 19 wątków obejmujących istniejące pule/Argon2, 20/20 przetworzonych, maks. ack 39,44 ms, czas 12,80 s. CPU z ps ma rozdzielczość pełnych sekund (2 s zarejestrowane), nie jest dokładnym benchmarkiem. Sam pomiar używa wątku obserwatora w narzędziu testowym, nie w aplikacji.

To mieści się w 512 MiB w badanym scenariuszu, ale **nie potwierdza pracy pod rzeczywistym limitem 0,5 CPU**, przy dużych burstach ani jednoczesnym procesie backupu. Istniejący backup buforuje dump/szyfrowanie w pamięci i pozostaje dodatkowym ryzykiem dla dużej bazy; nie zmieniono go w tej poprawce. Przed aktywacją wymagany monitoring RSS/OOM, opóźnienia inboxa i kontrola zbiegu backupu z obciążeniem. Pending/dead-letter wymagają ręcznego przeglądu, bo brak automatycznej retencji nierozwiązanych zdarzeń może powiększać bazę. Nie uruchomiono dodatkowych kosztów.

## 5. Plan wdrożenia — dopiero po pisemnej zgodzie

1. Zapisać aktualny produkcyjny commit/deploy jako rollback, odczytowy fingerprint wszystkich tabel i stan flag. Nie zakładać, że main jest aktualnym produkcyjnym deployem.
2. Świeży zaszyfrowany backup istniejącego PostgreSQL; odtworzyć na odizolowanej kopii i porównać liczby/SHA-256. Nie rotować META_ENCRYPTION_KEY. Żadnych wartości sekretów w raportach.
3. Na kopii upgrade 004 i pełna regresja. Po zgodzie migracja produkcyjna addytywna, z wyłączonymi modułami. Nie tworzyć nowej płatnej bazy/usługi.
4. Wdrożyć konkretny zaakceptowany commit na istniejący serwis, **META_DM_TRANSPORT_ENABLED=false**; OAuth/GET verify/ingest/history pozostają wyłączone aż do osobnego zatwierdzenia konfiguracji i odbioru. Nie mieszać dziedziczenia flag bez migracji opisanej w ENVIRONMENT.md.
5. Po zgodzie na odbiór przeprowadzić podpisany test webhooka **na koncie/aplikacji testowej**, potwierdzić commit, diagnostykę, deduplikację i CRM bez transportu DM. Nie wysyłać żadnych wiadomości Instagram. Samo przygotowanie podpisanego syntetycznego POST do aplikacji nie wymaga wysyłki DM.
6. Odczytowa kontrola danych po wdrożeniu i restarcie, weryfikacja health/commit, sesji i alertów. Włączenie odbioru rzeczywistego konta dopiero po osobnej zgodzie właściciela.

## 6. Wycofanie

- Wyłączyć jawnie wszystkie nowe flagi oraz legacy META_ENABLED; DM pozostaje false. Unikać tylko usunięcia nowych flag, bo nieobecne dziedziczą legacy.
- Zatrzymać konsumpcję przed cofaniem kodu. `alembic downgrade 003` zmienia revision, **zachowuje dwie nowe tabele i ich dane**. Ten logiczny rollback jest zamierzony i przetestowany; ponowny upgrade jest idempotentny. Nie wykonywać DROP na zaakceptowanym inboxie.
- Powrót do zapisanego ostatniego działającego commita/deployu z integracją wyłączoną. Stary kod nie przetwarza nowego inboxa; już zapisane CRM i ciphertext zostają. Ponowne uruchomienie 004 odzyskuje zaległości po przeglądzie właściciela.
- Kopię bazy odtwarzać wyłącznie po osobnej decyzji o danych nowszych od backupu; automatyczny overwrite byłby utratą danych i nie jest częścią rollbacku.

## 7. Zgody i otwarte pytania

- [x] Retencja zakończonych payloadów 7 dni / metadanych 90 dni, progi 100 / 300 s / dead-letter i cykl w istniejącym agencie zatwierdzone przez właściciela.
- [ ] Przegląd i akceptacja tej gałęzi; osobna zgoda na merge, wdrożenie, migrację i zmianę produkcyjnych flag.
- [ ] Osobna zgoda na autoryzację rzeczywistego @artur_uluru_hair i włączenie odbioru; IG user ID i role/configuration sprawdza właściciel w Meta.
- [ ] Ustalenie retencji i procedury rozwiązywania failed/dead-letter (nie kasujemy ich samodzielnie).
- [ ] Uzupełnienie administratora/podstawy prawnej/polityki prywatności; App Review/Advanced Access/live tylko po oddzielnej decyzji. Nie stanowią zakresu aktywacji tej poprawki.
- [ ] Weryfikacja Starter pod docelowym ruchem, w tym z backupem; żaden nowy koszt nie został zaakceptowany ani uruchomiony.
- [ ] Transport DM pozostaje niezaimplementowany i zablokowany. Nie jest następnym automatycznym krokiem wdrożenia.

Nie są potrzebne hasła, tokeny ani wartości sekretów w rozmowie. Dokładne nazwy i niesekretne URL-e są w ENVIRONMENT.md.

## 8. Pliki i kontrola zakresu

Kod: `backend/db.py`, `backend/main.py`, `backend/meta.py`, `backend/meta_models.py`, `backend/meta_flags.py`, `backend/meta_inbox.py`, `backend/meta_logging.py`, `backend/meta_refresh.py`, `backend/worker.py`, `frontend/src/MetaPanel.tsx`, `migrations/versions/004_meta_durable_inbox.py`.

Testy: `tests/conftest.py`, `tests/test_meta.py`, `tests/test_meta_303.py`, `tests/test_meta_migration.py`, `tests/meta_resource_probe.py`. Dokumentacja: `docs/meta/3.0.3/` (audyt bazowy, plan, konfiguracja, źródła Meta, ten raport i dowody).

`git diff main --stat` i `git diff main --name-only`: zmiany wyłącznie w powyższych plikach repozytorium **artgawlik-ui/ai-focus-3-0**. Focus 1.0 i 2.0 nie były przedmiotem żadnego zapisu, konfiguracji, migracji ani wdrożenia. Niezwiązane istniejące archiwa reports/*.zip pozostawiono nietknięte i nie dodano do commitów.

Dowody: [RESULTS.json](RESULTS.json), [backend JUnit](evidence/backend-junit.xml), [baseline JUnit](evidence/baseline-junit.xml), [E2E](evidence/browser-check.json), [zasoby](evidence/resources.json), [guard sieci](evidence/network-guard.json), [npm audit](evidence/npm-audit.json), [pip audit](evidence/pip-audit.json).
