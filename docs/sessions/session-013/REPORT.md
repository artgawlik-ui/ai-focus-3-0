# RAPORT AI FOCUS 3.0.4 — SESJA 013

## Punkt wejściowy i analiza

HEAD lokalny/GitHub a276463e161e43f933342c7c7ca7ab47f3e48b71 zgodny, CI 42090550994
success, PR #3 Draft. Odczytano RESUME, raport 012, RELEASE_GATE i architekturę README:
React/TS + FastAPI/SQLAlchemy/PG17, supervisor API/worker, schema 004. Osobnego dokumentu
architektury nie znaleziono. Zachowano poprawki 008–012 i prywatne archiwa (nie otwierano).

| Moduł | Rzeczywisty stan kodu |
|---|---|
| Odkrywanie salonów | Dotąd granice administracyjne miasta; teraz dodatkowo jawne centrum + promień 1–50 km za flagą OFF |
| Kwalifikacja/duplikaty | Reguły z uzasadnieniem/źródłem; dedup CRM nazwa+miasto; brak automatycznej weryfikacji danych publicznych |
| CRM/lejek | Profile, etapy, notatki, historia, import/eksport; istniejąca regresja API |
| Wizyty/trasy | Lokalne propozycje/statusy i konflikty; Maps wg godzin, brak optymalizacji ruchu/odległości |
| Google Calendar | Ręczny link do formularza; brak OAuth/synchronizacji |
| Zespół | Manager/handlowiec, przypisania/RBAC/KPI/szkolenia; bez nowej implementacji tych funkcji |
| Agent/odpowiedzi | Reguły, szkice, klasyfikacja odpowiedzi; provider opcjonalny OFF; Meta testowane mockami, realne konto niepotwierdzone |
| PWA | Manifest/ikony/SW/offline bez cache CRM; emulacja WebKit w CI, fizyczny iPhone historycznie potwierdzony przez właściciela |

## Implementacja użytecznej funkcji

- Dodano backend/discovery.py: geokodowanie miejscowości w Polsce (Nominatim), ręczny
  wybór przy niejednoznacznej nazwie, zapytanie Overpass around i odległość haversine.
- Endpoint /api/discovery/places wymaga sesji. /api/discovery z kompletem radius_km,
  latitude i longitude uruchamia promień; niepełny zestaw/niepoprawne wartości -> 422.
  Bez tych parametrów stare wyszukiwanie miasta zachowane.
- Granice 1–50 km, max 100 rekordów, post-filter odległości, dedup OSM type/id,
  weryfikacja typów/współrzędnych, bezpieczne błędy 503/429. Niepełna odpowiedź z remark
  nie udaje poprawnego kompletnego wyniku. Źródło, czas odczytu i status requires_manual_review.
- Nie wymyśla się miejscowości/specializacji/Instagram; pola nieznane puste.
  Nazwa zastępcza Salon bez nazwy wymaga ręcznego poprawienia/weryfikacji.
- Frontend DiscoveryPanel: przycisk geokodowania, lista miejscowości, promień,
  odległości/wyniki, formularz przeglądu przed zapisem. Źródło trafia do istniejącego
  source_url, data odczytu jako jawna notatka w profilu. Nie ma automatycznego zapisu,
  automatycznej kwalifikacji, DM ani wizyty. CRM nadal sprawdza duplikaty.
- DISCOVERY_RADIUS_ENABLED domyślnie false, bez zmiany starych flag. OFF ukrywa nowe UI
  i blokuje nowe ścieżki. GEOCODING_SEARCH_URL: HTTPS bez credentials/query/fragment,
  brak redirectów. Nie zmieniono produkcyjnej konfiguracji, zależności ani schematu.

## Źródła, limity i bezpieczeństwo

Oficjalna polityka Nominatim: https://operations.osmfoundation.org/policies/nominatim/
odczyt HTTP 200 5 listopada 2026. Potwierdzono max 1 request/s, User-Agent identyfikujący
aplikację, cache, zakaz autocomplete, możliwość zmiany usługi i zakaz danych poufnych.
Implementacja: przycisk zamiast autocomplete, cache 128 miejscowości/24 h w RAM,
nieblokujący slot lokalny i globalny pg_try_advisory_xact_lock z cooldown ≥1s.
Blokada transakcyjna jest współdzielona między API procesami, także podczas rolling deploy;
test PG sprawdza odmowę drugiego połączenia przed HTTP. Transakcja geokodowania zajmuje
jedno połączenie do timeoutu 10 s; nie kolejkuje dalszych żądań. Nie dodano instancji,
workera, Redis ani usług płatnych. SQLite nie daje rozproszonego limitu: nie jest produkcyjne.
Do geokodera trafia wpisana miejscowość, nie CRM ani kontakty. Cache zawiera publiczne
centra, nie klientów. Publiczne usługi mogą odmówić dostępu; brak gwarancji kompletności/SLA.

## Testy i wyniki

- `DATABASE_URL=postgresql://postgres@127.0.0.1:55432/focus3_test pytest -q tests/test_discovery_radius.py tests/test_api.py tests/test_qualification.py tests/test_agent_resilience.py`:
  **56 passed, 0 failed/skipped, 17.95 s**.
- **19 nowych przypadków**: promień/dystans, błędne dane, dedup, błędy upstream,
  uwierzytelnianie/flag OFF, zgodność city-only, brak automatycznego CRM, cache/rate limit,
  blokada między sesjami PostgreSQL, bezpieczne wyjątki. Wyłącznie mock HTTP/fixture.
- `npm run build --prefix frontend`: PASS (tsc i Vite). `git diff --check`: PASS.
- Dodano scenariusz UI w istniejącym E2E dla Chromium i WebKit/iPhone: wybór miasta,
  centrum/promienia, wynik i odległość, formularz przeglądu, zapis syntetycznego salonu,
  brak poziomego przewijania. Flaga promienia jest ON wyłącznie w izolowanym serwerze E2E;
  transport dostawców HTTP zastępują fixtures, przeglądarka używa rzeczywistego API. Nie jest to dowód działania prawdziwego Nominatim
  lub Overpass ani fizycznego iPhone'a. Końcowy wynik dopiero w CI dokładnego SHA.
- Brak realnych zapytań do usług wyszukiwania i brak komunikacji z klientami. Jedyny
  zewnętrzny HTTP nowej funkcji podczas sesji to odczyt oficjalnej polityki.
- README skorygowano: stare twierdzenie live 3.0.2 zastąpiono datowanym odczytem 012;
  usunięto instrukcję startu drugiego workera (start.sh już uruchamia supervisor).

## Dowody i blokady

Odrębna macierz: EVIDENCE_GATE.md — integralność, RPO60, magazyn/klucz, artefakt/env
rollbacku i handoff. Żadnego nierozwiązanego wymagania nie oznaczono PASS.
Polityka TCP odczytana jeden raz: domains/ip_ranges puste, VPN=false. Środowisko current,
running/connected. Brak udostępnionego narzędzia zmiany reguły; nie stosowano obejść.
**0 SSH, 0 SELECT.** A aktualna, prywatne tożsamości niepotwierdzone.
Wydanie nadal **BLOCKED**. Najbliższy krok operacyjny: aktywować ograniczony grant TCP
Codex do ssh.frankfurt.render.com:22, bez otwierania allowlisty PostgreSQL.
Po nim zweryfikować host/kanał/ID i wykonać tylko 4 zatwierdzone SELECT-y.
Najbliższy etap funkcjonalny po tej sesji: planowanie dostępnych terminów wizyt lub
integracja kalendarza na koncie testowym po osobnej autoryzacji; nie udawać obecnej synchronizacji.

## Zapis i ograniczenia

Pliki: backend/discovery.py, backend/main.py, frontend/src/DiscoveryPanel.tsx,
frontend/src/main.tsx, tests/test_discovery_radius.py, tests/production_browser_check.py,
.env.example, README.md, RESUME.md i dokumenty 013. Numery commitów w git log;
SHA raportu: `git log -1 --format=%H -- docs/sessions/session-013/REPORT.md`.
Końcowe CI i Draft PR #3 sprawdzić dla końcowego SHA; wynik w raporcie rozmowy i Checks.
Bez merge/deploy/zmian produkcji, eksportów/restore/PITR, klientów, sekretów i konfiguracji
Meta/Render/sieci. Brak realnych DM i nowych kosztów. Focus 1.0/2.0 niezmienione.
Szacunek nadal **5 sesji podstawowych + ≥1 DM**, bez redukcji za nową funkcję przy
otwartych wymaganiach recovery/dostępu. Nie działa w tle po sesji.

## Korekta po CI i dowody końcowego podejścia

CI cb64017 (42093723048): backend/build PASS (205 testów), Chromium nowy przepływ PASS,
WebKit nie znalazł przycisku geokodowania — testowa flaga nadpisywana przez browser route
nie dotarła do widoku kontrolowanego przez service workera. Nie zmieniono produkcyjnej flagi.
Usunięto zależność od interception przeglądarki: tests/ci_e2e.py włącza flagę tylko dla
swojego syntetycznego serwera. Izolowane sitecustomize ładuje tests/e2e_discovery_transport.py,
który zastępuje Nominatim/Overpass w httpx i blokuje wszystkie pozostałe zewnętrzne HTTP
(również Meta/model). Przeglądarka korzysta z rzeczywistego endpointu/geometrii/CRM.
Transport odmawia instalacji poza APP_ENV=test i lokalną bazą focus3_ci_*; nie ma importu
w kodzie aplikacji. Prywatny katalog fixture usuwany po E2E. Dodatkowe 4 testy guardów
transportu: **4 passed**, bez bazy i prawdziwej sieci. Łącznie **23 nowe przypadki pytest**
(19 funkcji +4 fixture), plus scenariusz UI w dwóch przeglądarkach.
Nowy końcowy commit/CI należy sprawdzić osobno; nie deklarować PASS na podstawie cb64017.

Bootstrap fixture kończy proces kodem 78 przy błędzie instalacji, ponieważ Python
domyślnie ignoruje wyjątki sitecustomize. Osobny test subprocess potwierdza brak startu
aplikacji poza dozwolonym środowiskiem, zamiast powrotu do rzeczywistego transportu.
