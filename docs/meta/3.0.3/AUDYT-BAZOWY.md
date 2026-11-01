# Ai Focus 3.0 — audyt Instagram tylko do odczytu, 2026-10-31

**Wniosek: aktualny kod nie pozwala bezpiecznie zakończyć konfiguracji dla @artur_uluru_hair bez zatwierdzonych poprawek. Nie zmieniono kodu aplikacji, ustawień produkcyjnych ani flagi, nie wykonano wdrożenia i nie wysłano wiadomości. Nie wykonywano rzeczywistych wywołań Instagram/Graph API.**

Repozytorium main: ba951fd43a0ef5d81e61457f7a541300e9b3b336. Render live: cd22a44415732a1e25b558bfec38cf498115b90f, dep-dbj59qff3r2c73f077u0. Różnice między tymi commitami dotyczą dokumentacji, nie kodu aplikacji. Publiczne HTTPS /api/health: 200, wersja 3.0.2, HSTS obecne. Źródło: read-only Render get_service/list_deploys i publiczny GET health. Nie sprawdzano ani nie zmieniano danych klientów na produkcji.

## 1. Właściwa ścieżka i poświadczenia

Kod buduje URL facebook.com/dialog/oauth z client_id, config_id, redirect_uri i response_type=code. Wywołania serwerowe używają graph.facebook.com/v26.0. To **Instagram API with Unified Login, zbudowane na Facebook Login for Business**. Wymagane są **Meta App ID/Secret**, nie Instagram App ID/Secret. Pierwszy docstring modułu myląco mówi Instagram Login; o faktycznej implementacji rozstrzygają hosty, parametry i rodzina tokenu.

Minimalne wymagane zakresy: instagram_basic i instagram_manage_messages. public_profile jest tolerowany jako ewentualny zakres niejawny; pozostałe są odrzucane. Konfiguracja Meta domyślnie może dodawać reklamy, komentarze i publikacje — trzeba potwierdzić ich usunięcie w panelu. Sam config_id nie jest poświadczeniem i nie dowodzi poprawnego sparowania z App ID/Secret.

Token to Business Integration System User Access Token (SUAT). Kod **nie realizuje klasycznego cyklu Instagram User token krótki → 60 dni → ig_refresh_token**. Dla Unified Login ten cykl byłby niewłaściwy. Czas ważności SUAT wybiera konfiguracja Meta. Endpoint /refresh tylko weryfikuje istniejący token i zwraca rotated=false; automatycznej rotacji nie ma. Token Management API wymaga dodatkowego business_management, którego kod nie żąda. Zastosowano ponowny OAuth przed wygaśnięciem i kontrolę ważności co dobę, wykonywaną podczas godzinnej pracy maintenance, gdy integracja jest aktywna.

## 2. Wszystkie META_* używane przez kod

Wymagalność poniżej dotyczy integracji Meta, nie działania bazowego CRM. Stany Render odczytano przez GET; żadna wartość nie została wypisana ani zapisana w raporcie. „Ustawione” nie oznacza potwierdzenia poświadczenia w Meta.

| Nazwa | Przeznaczenie | Wymagana? | Stan Render |
|---|---|---|---|
| META_ENABLED | Obecnie główna bramka funkcji Meta, nie tylko wysyłki | Opcjonalna; domyślnie blokada | ustawione |
| META_MODE | Lokalny tryb integracji; kod dopuszcza tylko tryb deweloperski | Tak dla integracji | ustawione |
| META_APP_ID | ID aplikacji Meta używane jako client_id | Tak | puste |
| META_APP_SECRET | Wymiana kodu, diagnostyka tokenu, podpisy webhooków i callbacków prywatności | Tak | puste |
| META_CONFIG_ID | Konfiguracja Facebook Login for Business / Unified Login | Tak | ustawione |
| META_VERIFY_TOKEN | Wspólny sekret sprawdzenia challenge webhooka | Tak w obecnym require_config | puste |
| META_ENCRYPTION_KEY | Szyfrowanie tokenów i treści w bazie | Tak | puste |
| META_TEST_ACCOUNT_ID | Dokładny identyfikator dopuszczonego profesjonalnego konta testowego | Tak | puste |
| META_REDIRECT_URI | Powrót OAuth, wspólny dla obu żądań | Tak | ustawione |

Dodatkowo PRIVACY_CONTROLLER_NAME i PRIVACY_CONTACT_EMAIL: oba **puste**. Nie są META_*, ale są potrzebne do kompletnej polityki prywatności przed App Review. BOOTSTRAP_EMAIL jest zależnością kodu rozpoznającego właściciela CRM; nie jest poświadczeniem Meta.

### Dokładny format klucza

backend/meta.py przekazuje META_ENCRYPTION_KEY.encode() do cryptography.fernet.Fernet. Biblioteka dekoduje URL-safe Base64 i wymaga **dokładnie 32 bajtów po dekodowaniu**. Standardowy klucz Fernet to **44 znaki URL-safe Base64, z końcowym znakiem =**. To nie dowolne hasło 32 znaków ani zapis hex.

Kod nie wymusza ścisłego formatu kanonicznego ani samej długości 44 znaków. Test wykazał, że biblioteka akceptuje również białe znaki otaczające poprawny klucz. Zalecany jest kanoniczny klucz bez cudzysłowów, spacji i nowych linii. Żadnego klucza nie wygenerowano ani nie wyświetlono do użycia produkcyjnego. Nie należy zmieniać istniejącego klucza po zapisaniu danych bez procedury ponownego szyfrowania.

## 3. Redirect URI

Oczekiwany adres:

https://ai-focus-3-0.onrender.com/api/meta/oauth/callback

Potwierdzono zgodność 1:1:

- render.yaml i odczyt konfiguracji Render;
- parametr redirect_uri w URL autoryzacji;
- parametr redirect_uri w serwerowej wymianie kodu.

Dwie ścieżki używają tej samej zmiennej, a test z mockiem sprawdził dosłowną równość, włącznie z HTTPS, wielkością liter i brakiem końcowego ukośnika. **Wartość wpisana w panelu Meta pozostaje do potwierdzenia przez właściciela.** require_config sprawdza jedynie prefiks HTTPS; nie chroni przed wpisaniem innego poprawnego adresu HTTPS. Zalecana jest dodatkowa walidacja oczekiwanego callbacka.

## 4. OAuth, bezpieczeństwo i znalezione blokady

Pozytywnie zweryfikowano: start wymaga zalogowanego menedżera, zgodności e-maila właściciela z BOOTSTRAP_EMAIL, CSRF i poprawnej konfiguracji. State jest losowy, haszowany, ważny 10 minut i związany z hashem sesji właściciela. Osobny Secure/HttpOnly/SameSite=Lax nonce chroni powrót z Meta; sama sesja CRM pozostaje SameSite=Strict. Callback weryfikuje aktywną sesję zapisaną w bazie, użytkownika i właściciela — nie musi otrzymywać ciasteczka Strict na powrocie. State jest atomowo zużywany, hash kodu unikalny. error/error_reason są obsługiwane; końcówka #_ jest usuwana. Token trafia jako szyfrogram Fernet do meta_credentials, nie do odpowiedzi API.

### Wymagane poprawki — nie wdrożono

1. **Blokada docelowego konta.** backend/meta.py:125 jawnie odrzuca username artur_uluru_hair i zwraca ogólny 502. Jest to zachowana blokada testowa, a nie odmowa Meta. Test z mockiem ją potwierdził. Nawet poprawne poświadczenia i konto zawodowe nie ominą tej reguły. Dla obecnego celu potrzebna jest zatwierdzona polityka kont/allowlista po trwałym ID i czytelny błąd lokalnej polityki zamiast sugestii problemu serwera Meta.
2. **Flaga blokuje konfigurację.** backend/meta.py:29–36 blokuje OAuth start/callback, GET/POST webhooka, subskrypcję, odczyt rozmów, szkice i zatwierdzenia. Sama obecność zmiennych nie wystarczy do wykonania OAuth przy pozostawionej blokadzie. Nie wolno traktować włączenia flagi jako rozwiązania bez osobnego zatwierdzenia.
3. **Wymaganie braku sekretów w URL-ach nie jest spełnione.** backend/meta.py:120 wysyła client_secret i code jako parametry GET wymiany kodu; :55 wysyła token jako input_token w query /debug_token. URL autoryzacji widoczny dla przeglądarki nie zawiera access tokenu ani App Secret, ale serwerowe URL-e je zawierają. Wyłączenie INFO httpx i access logów uvicorn ogranicza ekspozycję, lecz nie usuwa query stringu ani ryzyka logowania przez tracing/proxy. Aktualna dokumentacja Meta sama pokazuje GET dla wymiany kodu; nie należy zmieniać na nieudokumentowany POST bez weryfikacji. Trzeba potwierdzić wspieraną alternatywę lub jawnie uzgodnić wyjątek protokołu i redakcję we wszystkich warstwach.
4. **Chwilowa awaria usuwa poprawny token.** backend/meta.py:143–145 traktuje każdy błąd ręcznego /refresh jak unieważnienie. Mock ReadTimeout zakończył się 502, revoked=1 i wyczyszczeniem szyfrogramu. Timeout, 429 i 5xx powinny zachować poświadczenie; unieważnienie należy ograniczyć do jednoznacznego błędu grantu/wygaśnięcia. Endpoint ten nie jest rzeczywistą rotacją tokenu.
5. **Szybkie 200 webhooka nie jest gwarantowane.** Handler przetwarza całą paczkę i zapisuje CRM przed odpowiedzią; wykonuje synchroniczne SQL w async handlerze. Walidacja tokenu trzyma FOR UPDATE na meta_credentials podczas zewnętrznego żądania z timeoutem 20 s, a webhook czeka na ten sam rekord. Test współbieżny z mockiem wykazał, że odpowiedź webhooka nie kończy się przed zwolnieniem blokady maintenance. To może blokować nie tylko webhook, lecz również pętlę pojedynczego serwera. Należy skrócić transakcje, nie trzymać blokad podczas HTTP i przyjmować podpisane zdarzenie do trwałej kolejki/inboxa, a pełne przetwarzanie wykonać w istniejącym workerze.

Dodatkowe uwagi: error/error_reason są sprowadzane do „authorization_cancelled”, co utrudnia rozróżnienie odmowy i błędu konfiguracji; kod normalizuje #_ dwukrotnie, więc powinien robić to raz przed hashem i wymianą. Dobowa kontrola nie aktualizuje zapisanego expires_at po udanej diagnostyce. To rekomendacje przeglądu, bez zmian kodu. Nie można zagwarantować braku sekretów w historycznych/zewnętrznych logach wyłącznie na podstawie testów i konfiguracji loggera.

## 5. Webhook i statusy

Zgodne w kodzie/testach: GET sprawdza hub.mode i verify token porównaniem stałoczasowym oraz odsyła hub.challenge jako text/plain. POST sprawdza X-Hub-Signature-256 na **dokładnych bajtach surowego body**, przed JSON. Akceptuje tylko skonfigurowane konto testowe, stosuje transakcje, blokady i unikalność ID wiadomości w konwersacji. Duplikat nie tworzy drugiej aktywności; podpisane usunięcie nie jest odtwarzane późniejszą powtórką. Zapis odpowiedzi i powiązanie z salonem nie wysyłają wiadomości.

Obsługiwane są zdarzenia message, echo i deletion w polu messages. Inne typy są ignorowane; nie subskrybujemy read/delivery, nie deklarujemy potwierdzenia dostarczenia. manual_sent to oświadczenie właściciela, nie potwierdzenie API. Pierwsze niepowiązane rozmowy wymagają ręcznego dopasowania do salonu. Nie jest to pełna synchronizacja historycznej skrzynki.

Deduplikacja i HMAC są zweryfikowane, ale ograniczenie czasu odpowiedzi nie jest zapewnione — patrz blokada transakcyjna powyżej. Testy nie mierzyły SLA rzeczywistej dostawy Meta ani opóźnień produkcyjnej bazy.

## 6. META_ENABLED i proponowana zmiana

Potwierdzono kodem i testem z mockiem: przy wyłączonej fladze OAuth start/callback, webhook GET/POST, subscribe i refresh są odrzucane przed utworzeniem klienta Meta. Próba wywołania /messages/.../send nie ma handlera; licznik utworzeń klienta providera wyniósł 0. **Transport wysyłki nie istnieje również przy aktywnej fladze.** Przyznanie instagram_manage_messages samo nie tworzy funkcji DM.

Przy blokadzie pozostają dostępne status, lokalny disconnect oraz podpisane callbacki prywatności i Privacy Policy; retencja nadal działa. Odczyt odpowiedzi Meta przez agenta jest natomiast pomijany.

**Propozycja bez wdrożenia:** META_ENABLED przeznaczyć wyłącznie na twardą blokadę przyszłego transportu wysyłki. Oddzielić konfigurację i autoryzację od zgody na wysyłkę. OAuth, weryfikacja webhooka, podpisany ingest, odczyt historii i walidacja tokenu powinny działać przy kompletnej, zatwierdzonej konfiguracji, bez odblokowywania DM. GET challenge wymaga verify tokenu, a nie wszystkich poświadczeń OAuth. Zachować rolę właściciela, CSRF, allowlistę kont, podpisy i szyfrowanie. Statusy UI muszą rozróżniać połączenie, odbiór i zgodę na wysyłkę. Przyszły dispatcher wymaga dodatkowo zatwierdzenia każdej wiadomości/kampanii, poprawnego okna Meta, uprawnień i podstawy prawnej. Dzisiaj nie zmieniono semantyki flagi ani żadnego ustawienia.

## 7. Instrukcja paneli — do wykonania przez właściciela po decyzjach

### Render

Environment istniejącej usługi ai-focus-3-0: nazwy w tabeli powyżej. META_APP_ID/SECRET muszą pochodzić z **tej samej aplikacji Meta**, która zawiera wybraną konfigurację Unified Login. Nie używać Instagram App ID/Secret. META_TEST_ACCOUNT_ID to ID profesjonalnego konta, nie username, App ID ani Configuration ID. Szyfrowanego access tokenu nie wpisuje się ręcznie — powstaje z OAuth i jest przechowywany w bazie. Nigdy nie wysyłać wartości w rozmowie.

**Konkretny bezpieczny następny krok:** Render → ai-focus-3-0 → Environment → Edit: uzupełnić wyłącznie pola oznaczone puste, zweryfikować format klucza i zapisać przez **Save only**. Pozostawić przełącznik integracji bez zmian. Nie wybierać Save and deploy ani Save, rebuild, and deploy. „Save only” zapisuje konfigurację do następnego wdrożenia; nie zmienia zmiennych działającej instancji. To instrukcja dla właściciela — podczas audytu nie wykonano żadnego zapisu. Samo wypełnienie pól nie usuwa blokady konta i flagi; przed aktywacją wymagane są zatwierdzone poprawki.

### Meta Developers

Use cases → Manage messaging & content on Instagram → Customize → API setup with Unified login → Configure your app. Zweryfikować własność konfiguracji, token typu System-user, minimalne dwa uprawnienia i faktyczny czas życia. Ustawić dokładny Redirect URL. W Configure webhooks: Callback URL, Verify token (ta sama własna wartość co META_VERIFY_TOKEN w Render), pole messages. Konto po OAuth jest osobno subskrybowane do aplikacji; to nie uprawnienie do wysyłki.

| Pole panelu | Wartość niesekretna |
|---|---|
| Redirect URL / Valid OAuth Redirect URI | https://ai-focus-3-0.onrender.com/api/meta/oauth/callback |
| Webhooks Callback URL | https://ai-focus-3-0.onrender.com/api/meta/webhook |
| Webhook field | messages |
| Deauthorize Callback URL | https://ai-focus-3-0.onrender.com/api/meta/deauthorize |
| User Data Deletion — callback URL, nie instrukcje GET | https://ai-focus-3-0.onrender.com/api/meta/data-deletion |
| Privacy Policy URL | https://ai-focus-3-0.onrender.com/api/meta/privacy |

Wymagane jest konto zawodowe Business/Creator i odpowiednie business portfolio. Unified Login nie wymaga Facebook Page. Status zawodowy @artur_uluru_hair przyjęto jako deklarację właściciela, nie wynik zapytania API. Development wymaga ról aplikacji/Instagram Tester i zaakceptowanego zaproszenia; oficjalny przewodnik nie obsługuje zwykłych Meta Test Users. Rzeczywisty tryb aplikacji w Meta nie wynika ze zmiennej META_MODE i musi być sprawdzony w panelu. Dla osób spoza ról potrzebne są Live i Advanced Access po App Review; dokumentacja wymaga Business Verification dla dostępu produkcyjnego. Webhooks Setup wskazuje Live dla notyfikacji użytkowników, więc sama rola testera w Development nie gwarantuje rzeczywistej dostawy rozmów. Nie przełączać Live w ramach tego audytu.

Privacy Policy w aplikacji jest dokumentem testowym; brak tożsamości i kontaktu administratora wymaga uzupełnienia i przeglądu prawnego przed App Review. Deauthorize/data deletion weryfikują signed_request; niejednoznaczna tożsamość i reszta danych CRM trafiają do przeglądu administratora, nie są bezwarunkowo uznawane za usunięte. Nie ma potwierdzonej rzeczywistej konfiguracji tych pól w panelu Meta.

Pierwszego DM do dowolnego salonu API standardowo nie inicjuje. Otwarta rozmowa/okno Meta nie zastępują zgody marketingowej. Każda przyszła wysyłka wymaga zatwierdzenia; podczas audytu nie było transportu, rzeczywistych DM ani odpowiedzi automatycznych.

## 8. Render i usypianie

Odczyt get_service: Web Service / Docker, plan **Starter 0.5c-512mb**, jedna instancja, Frankfurt, niesuspendowana, auto-deploy wyłączony. Usługa nie jest Free. Reguła usypiania po 15 minutach bezczynności dotyczy Free i nie ma tu zastosowania. Nie potrzeba nowej usługi ani sztucznego keep-alive z tego powodu.

Starter nie eliminuje restartów, awarii, deployów ani blokad bazy. Obecnie większą przeszkodą jest blokada webhooka flagą i jego synchroniczne przetwarzanie. Wymagana trwała kolejka, idempotencja, monitoring i sprawdzone retry, a nie zmiana planu na podstawie reguły Free. Nie zmieniano planu ani kosztów.

## 9. Testy i rozdzielenie zakresu weryfikacji

- 49 istniejących testów regresyjnych: PASS. Pierwsze uruchomienie łączne z 5 próbami: 54 passed.
- 6 dodatkowych prób diagnostycznych: PASS, w tym późniejszy test współbieżnej blokady. Łącznie 49 + 6 unikalnych przypadków. Dodatnie wyniki prób diagnostycznych **potwierdzają opisane obecne zachowania/błędy**, nie są akceptacją produkcyjną.
- TypeScript/Vite build: PASS.
- E2E na lokalnej, świeżej, syntetycznej PostgreSQL: Chromium i WebKit/iPhone emulation PASS.
- pip-audit i npm audit: po 0 znanych podatności. Dwa ostrzeżenia deprecacji narzędzi testowych, bez awarii.
- Guard HTTP w testach: 0 prób ruchu zewnętrznego; dodatkowy guard procesów E2E nie odnotował próby Instagram/Graph. Wywołania Meta były mockami.

Komendy: `DATABASE_URL=<lokalna focus3_test> pytest -q -p network_guard tests /tmp/focus3-readonly-audit/test_audit_probes.py`; osobny przebieg 6 prób; `npm run build --prefix frontend`; `python -m tests.ci_e2e`; `pip-audit -r requirements.txt`; `npm audit --prefix frontend`. Dodatkowe testy i ich strażnik znajdują się wyłącznie w katalogu raportu/tymczasowym, nie w aplikacji. Testy nie korzystały z bazy produkcyjnej.

**Zweryfikowane w kodzie i mockach:** ścieżka OAuth, format klucza, zgodność URI po stronie aplikacji/Render, role/CSRF/state, szyfrowanie, podpisy i deduplikacja, brak sendera, blokada flagi i docelowego profilu, kasowanie tokenu po timeout oraz blokowanie odpowiedzi webhooka przez maintenance.

**Do potwierdzenia w panelach:** App ID/Secret należące do konfiguracji, typ SUAT i wygaśnięcie, dokładna lista grantów, rzeczywisty Meta Redirect URI, role i przypisanie konta/portfolio, tryb aplikacji, App Review/Business Verification, webhook subscription i delivery oraz kompletność polityki prywatności. Nie sprawdzano rzeczywistego OAuth na fizycznym iPhonie ani dostawy Meta. Nie ma podstaw do ogłoszenia gotowości integracji.

## Źródła — odczytano 2026-10-31

- https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-unified-login
- https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-unified-login/get-started
- https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-unified-login/authentication
- https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-unified-login/permissions
- https://developers.facebook.com/documentation/instagram-platform/webhooks/setup
- https://render.com/docs/free — Free idle spin-down 15 minut.
- https://render.com/docs/configure-environment-variables — znaczenie Save only.

Źródła kodu: backend/meta.py (linie 28–36, 54–61, 91–145, 155–220, 356–371), backend/security.py, backend/meta_models.py, backend/worker.py, scripts/supervise.py, render.yaml. Wyniki sanitowane w JSON/XML obok raportu. Wartości sekretów nie są zawarte w raporcie ani archiwum.

**Ai Focus 1.0 i 2.0 nie zostały zmodyfikowane. Nie wykonano żadnej mutacji Render, wdrożenia, włączenia META_ENABLED ani rzeczywistego wywołania Instagram/Graph API.**
