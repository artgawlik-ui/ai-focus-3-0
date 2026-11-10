# Issue 18 — decyzja kontraktowa i punkt wznowienia

Sprawdzenie: 10 listopada 2026. Baza: PR #17, `d8894b82c4989f4743fb8c254f46b631f5a96a48`. Osobna gałąź `feat/issue-18-meta-reply-guards`. Nie zmieniono produkcji ani PR #17.

## Decyzja: BLOCKED dla transportu

`contract_verified=false`, `can_send=false`. Nie zaimplementowano endpointu wysyłającego, klienta HTTP, receipt parsera ani fikcyjnej próby wysyłki. Żadna kombinacja flag nie odblokowuje wysyłki. Nie przenosimy kontraktu Instagram Login na Unified Login przez analogię.

| Element | Stan źródłowy | Dowód / brak |
|---|---|---|
| Produkt / login | unknown dla aktualnego outbound API | Kod używa Unified Login / Facebook Login for Business z config_id. Oficjalna strona [Unified Login](https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-unified-login) niedostępna w narzędziu podczas ponownego sprawdzenia. |
| Rodzaj tokenu | unknown | Lokalny walidator akceptuje SYSTEM_USER / BUSINESS_INTEGRATION_SYSTEM_USER; to nie dowód uprawnień wysyłkowych. [Authentication](https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-unified-login/authentication) wcześniej 429. |
| Scope | unknown | Istniejący kod: instagram_basic, instagram_manage_messages. [Permissions](https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-unified-login/permissions) ponownie 429. Nie potwierdzono wystarczalności. |
| Base URL / route | unknown | Istniejący adapter używa graph.facebook.com/v26.0; nie wybrano trasy wysyłki. [Graph v26](https://developers.facebook.com/docs/graph-api/changelog/version26.0/) niedostępne. |
| Sender IG ID / recipient IGSID | unknown jako kontrakt API | Lokalny podgląd porównuje account_id, sender/recipient w przetworzonym inboxie i external mid. Nie jest to weryfikacja rzeczywistego konta przez Meta. Brak prywatnych ID w raporcie. |
| Request / receipt | unknown | Nie implementujemy zgadywanego JSON ani potwierdzenia wysłania. |
| Okno, wyjątki i zasady odmowy | unknown | Wiek inbound jest informacją lokalną, nie kwalifikacją do okna 24h. Nie stosujemy domyślnych wyjątków ani okna Human Agent. |
| Wcześniejsza wiadomość użytkownika / Send API | documented_for_other_stack | Oficjalna [kolekcja Meta Postman](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api) opisuje Instagram Login i instagram_business_manage_messages. Nie potwierdza wybranej konfiguracji Unified Login / system-user token. |

Żaden element pełnego kontraktu outbound nie ma statusu `confirmed_for_exact_stack`. Niedostępność dokumentacji nie dowodzi, że funkcja nie istnieje; uniemożliwia bezpieczną implementację.

## Co istnieje w kodzie

- `GET /api/meta/replies/status`: jawny stan BLOCKED, brak transportu, zawsze can_send=false.
- `POST /api/meta/replies/{message_id}/check`: tylko autoryzowany właściciel, CSRF, lokalny podgląd bez zmiany statusu wiadomości. Odbiorca pochodzi z rozmowy, klient nie może go podmienić w payloadzie.
- Przetworzony, odszyfrowany inbox musi odpowiadać mid, kontu, senderowi, recipientowi i czasowi rzeczywistego inbound. Echo, szkic i zagregowana data nie zastępują inbound. Podpis jest kontrolowany przez istniejący ingest; podgląd korzysta z jego zaufanej ścieżki, nie twierdzi, że powtórnie weryfikuje surowy podpis.
- Blokady lokalne: opt-out CRM i rozmów, nieaktywny opiekun, niezgodne konto, wygasłe/odwołane/niedające się odszyfrować poświadczenie, brak powiązania salonu, nieaktualny fingerprint szkicu/rozmowy/poświadczenia.
- Fingerprint to snapshot, nie rezerwacja ani zgoda. Obecne ogólne zatwierdzenie szkicu nie jest zgodą API związaną z treścią i odbiorcą. Nie dodano trwałego ledgeru takich zgód.
- UI właściciela pokazuje wyłącznie sprawdzenie warunków, przyczyny blokady i wiek inbound. Nie ma przycisku wysyłki API.

## Flagi i granice

`META_REPLY_PREVIEW_ENABLED`: domyślnie OFF, tylko dosłowne true po normalizacji włącza podgląd. `META_REPLY_TRANSPORT_ENABLED`: domyślnie OFF; nawet true wraz z istniejącą META_DM_TRANSPORT_ENABLED kończy się odmową 501, bez I/O. Brak/pusta/błędna wartość daje odmowę 403. Semantyka istniejących flag pozostaje niezmieniona. Flagi testowe są ustawiane wyłącznie w syntetycznym E2E, nie w Render.

Nie wykonano OAuth, wysyłki, zmian bazy produkcyjnej, migracji, deployu ani zmian sekretów. Focus 1.0/2.0 pozostają bez zmian. Nie aktywowano Google ani automatyzacji płatnego AI.

## Testowanie i brakujące dowody

Nowy moduł `tests/test_meta_reply_preflight.py`: 31 scenariuszy syntetycznego PostgreSQL 17: RBAC, CSRF, podpis/replay, dowód inbound, opt-out, poświadczenia, zmiany snapshotu, równoległe podglądy i odmowa transportu przy wszystkich flagach ON. Test blokuje tworzenie klienta HTTP podczas próby transportu. Wynik i dokładny SHA/pełne CI należy odczytać w raporcie Issue #18 / Draft PR po zakończeniu przebiegu.

E2E rozszerza istniejącą ścieżkę Meta o podgląd blokady i brak przycisku wysyłki w Chromium/WebKit. Testy request/receipt, timeoutów wysyłki, 429/5xx Meta oraz rzeczywistego okna są BLOCKED, nie wykonane i nie przedstawiane jako PASS. Nie powstał pozorny mock poprawnej wysyłki.

Przed przyszłym transportem wymagane: udokumentowany dokładny kontrakt; trwała zgoda właściciela związana z aktualną treścią i odbiorcą; ledger prób i receipt; końcowa transakcyjna kontrola sesji/roli/opiekuna/opt-out/inbound/tokenów; fencing współbieżności; niejednoznaczny timeout bez automatycznej ponownej wysyłki; dopiero receipt uzasadnia potwierdzone wysłanie. Dzisiejszy podgląd tego nie zastępuje.

## Jedyny następny krok

Właściciel otwiera zgłoszenie w oficjalnym Meta Developer Support i przekazuje poniższe pytanie, bez sekretów ani prywatnych identyfikatorów. Nie kontaktowaliśmy się z Support w jego imieniu.

> Proszę wskazać aktualną oficjalną dokumentację odpowiedzi na istniejącą rozmowę Instagram dla Instagram API with Unified Login / Facebook Login for Business z system-user tokenem i zakresem instagram_manage_messages, Graph API v26.0: obsługiwany typ tokenu i wymagane scope, base URL i route, identyfikatory sender IG ID/recipient IGSID, request/receipt, standardowe okno odpowiedzi i dozwolone wyjątki. Czy ta konfiguracja obsługuje tę operację i czy różni się od Instagram Login z instagram_business_manage_messages? Proszę o linki dotyczące dokładnie tej ścieżki.

Do uzyskania jednoznacznego źródła: transport BLOCKED, integracja produkcyjna NO-GO. Nie wymaga to przekazywania kluczy ani tokenów do rozmowy.
