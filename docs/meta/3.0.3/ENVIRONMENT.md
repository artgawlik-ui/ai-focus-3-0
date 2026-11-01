# Konfiguracja 3.0.3 — propozycja, nie zastosowano w Render

Ścieżka: **Instagram API with Unified Login / Facebook Login for Business**, konfiguracja `config_id`. Używa **Meta App ID / App Secret**, nie Instagram App ID/Secret. Wymagane scope: `instagram_basic` (identyfikacja konta), `instagram_manage_messages` (odbiór wiadomości). `public_profile` dopuszczone jako implicit; inne scope odrzucane. `business_management` nie jest żądane. Nie stosujemy ig_refresh_token przeznaczonego dla innej ścieżki.

## Flagi

| Nazwa | Domyślna / zachowanie | Użycie |
|---|---|---|
| META_ENABLED | false; dotychczasowe parsowanie lower()==true bez zmian | legacy default wszystkich modułów |
| META_MODE | brak blokuje; wyłącznie development | strażnik trybu dla modułów, bez przełączenia live |
| META_OAUTH_ENABLED | brak dziedziczy legacy; jawna pusta/błędna=false | start/callback/refresh/maintenance tokenu |
| META_WEBHOOK_VERIFY_ENABLED | jak wyżej | wyłącznie GET challenge |
| META_INGEST_ENABLED | jak wyżej | POST trwałego inboxa i ręczna subskrypcja messages |
| META_CRM_HISTORY_ENABLED | jak wyżej | procesor inboxa, historia/szkice/powiązania i wejście odpowiedzi do agenta |
| META_DIAGNOSTICS_ENABLED | jak wyżej | status poświadczenia i owner-only diagnostyka inboxa |
| META_DM_TRANSPORT_ENABLED | **false, niezależnie od wszystkich pozostałych**; brak/pusta/błędna=false | sprawdzana wewnątrz send_dm; true kończy się 501, brak implementacji HTTP |

Nieobecne flagi modułów zachowują również dawny wymóg kompletu siedmiu zmiennych. Jawne override oznacza migrację do wymogów właściwych dla modułu. To migracja konfiguracji, a nie zmiana wartości w Render. Disconnect i podpisane callbacki prywatności pozostają dostępne także przy wyłączonych modułach.

## Zmienne (wartości właściciel wpisuje wyłącznie w Render)

- META_APP_ID, META_APP_SECRET: aplikacja Meta obsługująca Unified Login (OAuth, podpis POST i signed_request).
- META_CONFIG_ID: konfiguracja Facebook Login for Business; potwierdzone przez właściciela ID 2380634476006078 wymaga sprawdzenia przypisania do właściwej aplikacji w panelu.
- META_TEST_ACCOUNT_ID: **dokładny zatwierdzony IG user ID**, nazwa profilu nie zastępuje tego ID. Nie zmieniono nazwy zmiennej, aby zachować kompatybilność; profesjonalny profil właściciela dopuszczony po zgodzie i oficjalnej konfiguracji.
- META_VERIFY_TOKEN: sekret uzgodnienia GET webhooka.
- META_ENCRYPTION_KEY: dotychczasowy klucz Fernet, **32 bajty zakodowane URL-safe Base64 (kanonicznie 44 znaki)**; walidacja jest wykonywana przez bibliotekę, bez osobnego regexu; kod weryfikuje `Fernet(value.encode())`. Nie rotować. Istniejący format ciphertext `{kind,value}` zachowany.
- META_REDIRECT_URI: `https://ai-focus-3-0.onrender.com/api/meta/oauth/callback` — bez końcowego `/`. Ta sama wartość w dialogu i wymianie kodu.
- BOOTSTRAP_EMAIL: istniejąca tożsamość właściciela (poza prefiksem Meta); konto manager + zgodny email + aktywna sesja. Nie podajemy wartości w raporcie.
- PRIVACY_CONTROLLER_NAME, PRIVACY_CONTACT_EMAIL: wymagają uzupełnienia przez właściciela przed rzeczywistym uruchomieniem/App Review.

## Pola panelu Meta (tylko instrukcja, bez zmian)

- Facebook Login for Business / Configurations: istniejąca Unified Login; zweryfikować rodzaj tokenu SYSTEM_USER i powyższe minimalne scope.
- Valid OAuth Redirect URIs: `https://ai-focus-3-0.onrender.com/api/meta/oauth/callback`
- Webhooks / Instagram / Callback URL: `https://ai-focus-3-0.onrender.com/api/meta/webhook`
- Verify token: wartość z META_VERIFY_TOKEN wpisana w panelu, nigdy w rozmowie.
- Subscribed fields: **messages**. Brak rozszerzania na inne zdarzenia i automatycznych odpowiedzi.
- Deauthorize callback URL: `https://ai-focus-3-0.onrender.com/api/meta/deauthorize`
- Data deletion request URL: `https://ai-focus-3-0.onrender.com/api/meta/data-deletion`
- Privacy Policy URL: `https://ai-focus-3-0.onrender.com/api/meta/privacy`

Kod pozostaje development-only. Role testerów i uprawnienia do konta zawodowego, konfigurację aplikacji, ewentualny App Review/Advanced Access i business verification trzeba potwierdzić w panelu; sam config_id nie dowodzi spełnienia wymagań. Nie przełączono live, nie składano wniosków. API nie daje prawa do cold DM dowolnym salonom; w tej poprawce każdy transport DM jest nieosiągalny.
