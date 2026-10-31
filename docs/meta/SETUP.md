# Meta / Instagram — Unified Login, 2026-10-31

## Wybrana ścieżka

Właściciel podał Configuration ID 2380634476006078 i nazwę Unified Login. Aktualna dokumentacja Meta jednoznacznie opisuje tę ścieżkę jako Instagram API with Unified Login, zbudowaną na Facebook Login for Business. Używamy Meta App ID/Secret, config_id, logowania przez facebook.com/dialog/oauth i Graph API **v26.0** pod graph.facebook.com. Nie używamy Instagram App ID/Secret, instagram_business_* ani graph.instagram.com. Sam Configuration ID nie daje dostępu do panelu i nie potwierdza ustawionych uprawnień, typu tokenu ani konta.

Unified Login zwraca Business Integration System User Access Token (SUAT), nie Instagram User token. Wymiana kodu po stronie serwera daje token o czasie życia wybranym w konfiguracji. Nie stosujemy niepoprawnego dla tej ścieżki ig_exchange_token / ig_refresh_token i nie zakładamy automatycznie 60 dni. /me oznacza system user; konto Instagram odczytujemy z /me/assigned_instagram_accounts, a client_business_id oddzielnie z /me.

## Minimalne uprawnienia

- instagram_basic: odczyt identyfikatorów kont Instagram udostępnionych aplikacji.
- instagram_manage_messages: odbiór zdarzeń i treści rozmów oraz wymagane przez Meta możliwości messaging. Aplikacja Ai Focus nie posiada endpointu wysyłki.

Konfiguracja domyślna Meta może zawierać dodatkowo comments, content_publish, ads_management i ads_read. Należy je usunąć w Edit permissions. Callback odrzuca nadmiarowe uprawnienia; toleruje wyłącznie public_profile, jeśli platforma nada je niejawnie. Nie żądamy e-mail, reklam, publikowania ani business_management. Ten ostatni byłby wymagany do Token Management API; bez niego plan obejmuje dobową kontrolę ważności i ponowny OAuth przed wygaśnięciem. Właściciel może ręcznie sprawdzić ważność i lokalnie odłączyć konto. Po wykryciu unieważnienia token jest kasowany lokalnie, a ingest blokowany.

## Dokładne URL-e, bez końcowego ukośnika

| Cel | URL |
|---|---|
| OAuth Redirect URL | https://ai-focus-3-0.onrender.com/api/meta/oauth/callback |
| Webhook GET/POST | https://ai-focus-3-0.onrender.com/api/meta/webhook |
| Deauthorize callback POST | https://ai-focus-3-0.onrender.com/api/meta/deauthorize |
| Data deletion callback POST | https://ai-focus-3-0.onrender.com/api/meta/data-deletion |
| Privacy Policy URL | https://ai-focus-3-0.onrender.com/api/meta/privacy |

OAuth rozpoczyna wyłącznie właściciel przez uwierzytelniony POST /api/meta/oauth/start z CSRF. State ważny 10 minut, związany z aktywną sesją właściciela i osobnym ciasteczkiem Secure/HttpOnly/SameSite=Lax. Oryginalna sesja CRM pozostaje SameSite=Strict. Callback akceptuje powrót bez ciasteczka Strict, weryfikując zachowaną sesję w bazie i nonce Lax; odrzuca powtórkę state i ponowny hash kodu. Obsługuje error/error_reason, usuwa końcówkę #_ z kodu i nie zwraca tokenów. Brak kodu/anulowanie nie inicjują wywołania Meta.

## Render — wyłącznie nazwy zmiennych

Publiczna konfiguracja w render.yaml: META_ENABLED, META_MODE, META_CONFIG_ID, META_REDIRECT_URI. Domyślnie integracja wyłączona, tryb tylko development. Wartości sekretów właściciel wpisuje sam w Render → ai-focus-3-0 → Environment:

- META_APP_ID — ID aplikacji Meta; nie Configuration ID ani Instagram App ID.
- META_APP_SECRET — App Secret tej samej aplikacji Meta.
- META_VERIFY_TOKEN — osobny, losowy sekret weryfikacji webhooka.
- META_ENCRYPTION_KEY — trwały klucz Fernet o 32 bajtach zakodowanych base64; przechowywany i backupowany oddzielnie od bazy. Nie zmieniać bez procedury ponownego szyfrowania.
- META_TEST_ACCOUNT_ID — ID odrębnego profesjonalnego konta testowego przypisanego do aplikacji; nie konto docelowe właściciela.
- PRIVACY_CONTROLLER_NAME — rzeczywista tożsamość administratora danych.
- PRIVACY_CONTACT_EMAIL — kontakt w sprawach danych osobowych.

Wartości nie trafiają do rozmowy, repozytorium ani raportów. Token uzyskany w OAuth zapisuje serwer jako szyfrogram w PostgreSQL; nie trzeba przeklejać access tokenu. Złe klucze blokują integrację, nie CRM. Nie przyznajemy aplikacji dostępu do Render API.

## Panel Meta i konto testowe

Wymagane: aplikacja należąca do business portfolio, use case Manage messaging & content on Instagram i konfiguracja kompatybilna z Instagram Login, typu System-user access token. Unified Login nie wymaga Facebook Page. Konto musi być zawodowe: business lub creator, w odpowiednim portfolio. Nie ustalono typu @artur_uluru_hair ani jego uprawnień — brak autoryzowanego dostępu do ustawień.

Pozostawić Development. Standard Access służy osobom z rolami aplikacji. Do testów potrzebne rzeczywiste, odrębne profesjonalne konto Instagram dodane jako Instagram Tester i zaakceptowane zaproszenie: Instagram web → Settings → Website permissions → Apps and websites → Tester Invites. Oficjalny przewodnik Unified Login wskazuje, że zwykłe Meta Test Users nie są obsługiwane. Kod odrzuca autoryzację nazwy konta docelowego artur_uluru_hair.

Konfiguracja: App Dashboard → Use cases → Manage messaging & content on Instagram → Customize → API setup with Unified login → Configure your app → konfiguracja 2380634476006078 → Redirect URL. Ustawić dokładny adres z tabeli. W preview sprawdzić typ i czas życia tokenu, a w Edit permissions pozostawić minimalny zakres. Osobno Configure webhooks: callback z tabeli i verify token z bezpiecznej konfiguracji; subskrypcja tylko messages. Dopiero jawny przycisk właściciela subskrybuje konto testowe; webhook nigdy nie uruchamia odpowiedzi.

Dla osób spoza ról: Live, Advanced Access/App Review dla obu uprawnień i wymagana przez Meta weryfikacja biznesowa. Nie przełączano Live, nie wysyłano wniosków App Review ani nie inicjowano komunikacji produkcyjnej. Privacy Policy i callbacki deauthorize/data deletion muszą być dostępne; polityka jest obecnie dokumentem testowym, wymaga uzupełnienia tożsamości administratora oraz zatwierdzenia podstaw prawnych i procesorów przed App Review.

## Wiadomości, dane i ograniczenia

API nie pozwala rozpocząć rozmowy z dowolnym profilem. Standardowo użytkownik musi najpierw napisać. Lokalny panel wskazuje konserwatywne 24-godzinne okno na podstawie czasu zdarzenia, nie czasu odbioru webhooka. Dokumentacja Meta opisuje szczególne okna CTD/Human Agent; nie są włączone ani traktowane jako zgoda marketingowa. Pierwszy kontakt pozostaje szkicem do ręcznego wysłania po zatwierdzeniu i sprawdzeniu podstawy prawnej. Każda wiadomość i wizyta wymaga decyzji właściciela.

Webhook: challenge GET z verify tokenem, POST HMAC-SHA256 na dokładnych bajtach body, tylko skonfigurowane konto testowe, limit rozmiaru, transakcyjna deduplikacja po ID wiadomości i konwersacji, tombstone usunięcia chroniący przed późną powtórką. Nie pobieramy załączników ani URL-i odbiorcy. Niesubskrybowane typy zdarzeń są ignorowane; read/delivery nie są zaimplementowane. Nie utożsamiamy odczytu ze statusem dostarczenia.

Statusy: draft, approved (niewysłana), manual_sent (oświadczenie właściciela, bez potwierdzenia dostarczenia), api_confirmed_sent (podpisane echo), received (podpisana wiadomość przychodząca), deleted. Nie ma statusu wysłania na podstawie samego szkicu ani prób wysyłki — transport wysyłkowy nie istnieje. Konwersację wiąże menedżer z salonem po ręcznej weryfikacji; handlowiec widzi wyłącznie przypisane salony. Agent odczytuje potwierdzone odpowiedzi z zachowaniem źródła i generuje szkic wizyty 15–20 minut, przedstawiający reprezentanta NAK Hair/muk Haircare, bez oferty produktów i cen.

Treść i tokeny szyfrowane Fernet. Treść starsza niż 30 dni nie jest ujawniana, fizyczne czyszczenie co godzinę; minimalne ID wiadomości usuwane po 90 dniach. Rezygnacja blokuje szkice. Potwierdzenia API nie stanowią zgody na marketing. Wyłączono surowe logi dostępu uvicorn i INFO httpx; log audytowy zapisuje szablon trasy, konto i status bez query/body. Nie włączać debugowania HTTP ani rejestrowania parametrów OAuth w zewnętrznych narzędziach.

Data deletion/deauthorize wymagają poprawnego signed_request. Usunięcie czyści lokalny token i treści integracji oraz blokuje dalszy ingest bez nowego OAuth. Dane CRM, kopie i niejednoznaczna tożsamość wymagają weryfikacji administratora; status nie twierdzi, że całe RODO zostało automatycznie wykonane. Publiczny status żądania nie ujawnia danych klienta. Uprawnienia po stronie Meta właściciel odwołuje w Business Settings → Integrations → Connected apps. Lokalny disconnect nie oznacza zdalnego cofnięcia grantów.

## Koszty i stan weryfikacji

Nie utworzono nowych usług ani nie aktywowano płatnych API, reklam i modelu AI. Dotychczasowy bazowy koszt Render pozostaje około 13 USD/mies. plus podatki/ponadlimitowe zużycie. Dokumentacja wdrożonych przepływów OAuth/webhook nie wskazuje opłaty za konfigurację; nie jest to obietnica bezpłatności każdego przyszłego produktu Meta.

Testy transportu Meta są atrapami na danych syntetycznych. Rzeczywiste wydanie tokenu, konto testowe, uprawnienia w konfiguracji, dostawa webhooka i warunki App Review pozostają niezweryfikowane do bezpiecznego wpisania zmiennych i osobistej autoryzacji. Wdrożenie kodu z flagą wyłączoną nie oznacza połączenia z Instagramem. Schemat ma pięć nowych tabel; przed migracją wymagany zaszyfrowany backup, odtworzenie na kopii i zgodność dziewięciu istniejących tabel CRM. Bezpośredni rollback do df78fd7 nie rozpoznawałby rewizji 003. Przygotowano gałąź rollback/phase2-meta-schema, commit 4c2eedf: zachowanie poprzedniego wydania df78fd7 plus wyłącznie znajomość dodatkowego schematu. Nie kasujemy tabel Meta i nie wykonujemy destrukcyjnego downgrade; wynik CI i testu zgodności są w raporcie wdrożenia.

## Źródła — odczytano 2026-10-31

1. https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-unified-login — wybór ścieżki, portfolio, host i typ tokenu.
2. https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-unified-login/get-started — config_id, dokładne parametry OAuth, konta testowe, ID i menu panelu.
3. https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-unified-login/authentication — SUAT, wygaśnięcie zależne od konfiguracji, unieważnienie.
4. https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-unified-login/permissions — instagram_* i business_management dla Token Management API.
5. https://developers.facebook.com/docs/facebook-login/facebook-login-for-business/ — konfiguracje, system_user_access_tokens i wymagania uprawnień.
6. https://developers.facebook.com/documentation/instagram-platform/webhooks/setup — podpisy, callbacki i wymagania produkcyjne.
7. https://developers.facebook.com/documentation/instagram-platform/webhooks/examples — formaty wiadomości i identyfikatory.
8. https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/messaging-api/ — ograniczenia inicjowania, okien i długości wiadomości; nie jest źródłem wyboru OAuth dla Unified Login.
