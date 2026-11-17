# Instrukcje właściciela — przygotowanie, bez aktywacji

Sprawdzono 1 listopada 2026 (Europe/Warsaw). Nie wykonano żadnej z poniższych zmian w panelach.

## Render: minimalny krok i dwa odrębne warunki dostępu

Następny krok właściciela: **Render Dashboard → Account settings → SSH Public Keys → + Add SSH Public Key**:
dodać publiczną część zatwierdzonego klucza środowiska wykonawczego. Klucz prywatny pozostaje
w bezpiecznym magazynie; nie wysyłać go w rozmowie, GitHub ani raportach.
Nie generowano klucza w tej sesji: ulotny klucz bez zatwierdzonego magazynu nie zapewnia trwałego dostępu.

Drugi niezależny warunek: administrator środowiska Codex musi dopuścić ograniczony TCP
do `ssh.frankfurt.render.com:22`. Bieżący odczyt polityki: brak domen/IP TCP, brak VPN.
Dodanie klucza w Render samo nie usuwa tej blokady. Nie obchodzimy proxy, nie otwieramy
publicznej allowlisty PostgreSQL, nie wystawiamy SQL przez HTTP ani nowej usługi.
Oficjalne źródło: https://render.com/docs/ssh — HTTP 200; potwierdzono nazwy pól panelu.
Render Shell istniejącej usługi może być alternatywą tylko po uzgodnieniu operatora
oraz zatwierdzeniu dostępu. Nie twierdzimy, że agent widzi ten panel lub ma już SSH.

Po skonfigurowaniu i osobnym dopuszczeniu kanału: uruchomić zatwierdzony kod
`scripts/readonly_preflight.py` jako moduł w zatwierdzonym środowisku narzędziowym
istniejącej usługi, korzystając z już dostępnego wewnętrznego DATABASE_URL.
Nie deployować gałęzi tylko po to, aby udostępnić skrypt; transfer i wykonanie narzędzia
na serwerze są osobną czynnością wymagającą zgody. Nie instalować pakietów w produkcji.
Nie importować backend.main, nie uruchamiać bootstrapu, migracji ani workerów.
Przykład PRZEGLĄDOWY przyszłego wywołania (NIEWYKONANY):

```sh
python -m scripts.readonly_preflight \
  --manifest <zatwierdzony-manifest> \
  --approved-internal-readonly
```

Opcjonalne `--technical-user-id` i `--owner-user-id` wyłącznie po jednoznacznym wskazaniu
przez właściciela; brak tych argumentów daje `not_checked`, nie potwierdzenie kont.
Nie używać nazwy konta do zgadywania identyfikatora. Aktywne konto właściciela w SQL
nie stanowi dowodu udanego logowania. Weryfikacja sesji technicznej obejmuje wszystkie sesje.
Wyjście zawiera tylko zgodność manifestu, liczby i statusy; nie zawiera ID, danych ani tokenów.
Preflight nie potwierdza świeżości backupu/klucza ani nie autoryzuje cleanup.
Historyczny zakres 13 rekordów nadal wymaga aktualnego odczytu. Każda różnica: BLOCKED.

## Meta: konfiguracja developerska

Ścieżka kodu: **Instagram API with Unified Login**, oparta na **Facebook Login for Business**.
Poświadczenia: Meta App ID / App Secret, nie Instagram App ID / Secret.
Configuration ID identyfikuje konfigurację, nie jest dowodem jej poprawności.
Kod używa `graph.facebook.com/v26.0`; dokumenty setup są bez numeru wersji,
nie potwierdzaliśmy realnym API dostępności v26.0 dla konkretnej aplikacji.

1. **Meta App Dashboard → Use cases → Manage messaging & content on Instagram → Customize → API setup with Unified login**.
   Aplikacja musi należeć do business portfolio. Zachować Development.
2. **Configure your app**: sprawdzić istniejącą konfigurację; musi mieć etykietę
   **Instagram Login Compatible**. Nie tworzyć drugiej, jeśli istniejąca jest prawidłowa.
3. W podglądzie **Edit permissions**: pozostawić `instagram_basic` i
   `instagram_manage_messages`. Pierwsze pozwala rozpoznać udostępnione konto;
   drugie jest wymagane do messaging. Usunąć domyślne reklamy/publikowanie/komentarze,
   bo callback kodu odrzuca nadmiarowe zakresy. Nie dodawać `business_management`
   tylko w celu przygotowania testów. Nie używać `instagram_business_*` z innej ścieżki.
4. **Redirect URL**: dokładnie `https://ai-focus-3-0.onrender.com/api/meta/oauth/callback`,
   bez końcowego ukośnika. Nie rozpoczynać OAuth na produkcji w tej sesji.
5. **Generate access tokens → Add account**: instrukcja przygotowania konta testowego,
   nie polecenie generowania/udostępniania tokenu. Zaprosić odrębne zawodowe konto testowe
   jako Instagram Tester. Zaproszenie przyjąć na Instagram WWW: **Settings → Website permissions → Apps and websites → Tester Invites**.
   Nie używać @artur_uluru_hair do testów bez odrębnego dopuszczenia konta docelowego.
6. IG user ID musi być identyfikatorem konta zawodowego udostępnionego aplikacji.
   `/me` dla SUAT oznacza system user; kod używa `/me/assigned_instagram_accounts`.
   Odczyt tego ID przez API dopiero w zatwierdzonym teście OAuth. Nie zgadywać ID po nazwie profilu.
7. Standard Access pozwala na testy osób z rolą w aplikacji. Inni klienci wymagają
   Advanced Access przez **Complete App Review → Go to app review** oraz Live;
   nie wnioskowano o dostęp i nie przełączano trybu. Business verification jest wymagana
   dla production access według dokumentacji webhooków. Faktyczny stan panelu nieznany.

### Istotna granica testów webhooka

Aktualna dokumentacja setup mówi: „Your app must be published or Live to receive
notifications for app users”. Nie obiecujemy rzeczywistych powiadomień w Development
na podstawie testów OAuth ze Standard Access. Sprawdzian callbacka lub fixture nie
potwierdza dostawy wiadomości. Jeśli właściciel wymaga wyłącznie Development,
rzetelna walidacja dostarczania pozostaje BLOCKED do rozstrzygnięcia dopuszczonego
scenariusza testowego przez Meta; nie przełączamy aplikacji w Live w ramach obejścia.

### Pola przygotowane, nieaktywowana konfiguracja

| Pole | Wartość niesekretna |
|---|---|
| Redirect URL | https://ai-focus-3-0.onrender.com/api/meta/oauth/callback |
| Webhook Callback URL | https://ai-focus-3-0.onrender.com/api/meta/webhook |
| Subscribed fields | tylko `messages`; brak obietnicy read/delivery |
| Deauthorize callback URL | https://ai-focus-3-0.onrender.com/api/meta/deauthorize |
| Data deletion callback URL | https://ai-focus-3-0.onrender.com/api/meta/data-deletion |
| Privacy Policy URL | https://ai-focus-3-0.onrender.com/api/meta/privacy |

Verify Token wpisuje właściciel bezpiecznie, nie w rozmowie. Produkcyjny endpoint
weryfikacji może pozostać wyłączony; nie zapisywać konfiguracji powodującej realne
wywołanie callbacka bez osobnej zgody. Żadnego realnego Graph/OAuth/DM w tej sesji.

Nazwy ustawień poufnych przyszłej konfiguracji: `META_APP_SECRET`, `META_VERIFY_TOKEN`,
`META_ENCRYPTION_KEY`; pozostałe `META_APP_ID`, `META_CONFIG_ID`, `META_TEST_ACCOUNT_ID`,
`META_REDIRECT_URI`, `META_MODE`. Wartości wyłącznie w zatwierdzonym magazynie,
po osobnym zatwierdzeniu zmian. Nie rotować klucza Fernet (32 bajty urlsafe-base64).
Wszystkie flagi `META_*_ENABLED` i `META_ENABLED` mają pozostać wyłączone;
`META_DM_TRANSPORT_ENABLED=false` niezależnie od pozostałych.

## Retencja i RODO — warunki uruchomienia

Zatwierdzone wcześniej: payload done 7 dni, metadane inboxa 90 dni, alert pending≥100,
najstarsze pending>5 minut lub dead-letter≥1. Wiadomości: treść 30 dni, ID 90 dni.
Failed/dead-letter wymagają osobnej polityki dostępu i bezpiecznego czyszczenia;
nie przedstawiamy retencji zakończonych jako automatycznej retencji wszystkich błędów.
Właściciel wskazuje administratora, kontakt RODO, cel/podstawę prawną i reguły rezygnacji.
Dostęp API nie jest zgodą na marketing; każda wiadomość wymaga zatwierdzenia.
Nie przenosić treści/ID/tokenów do logów. Recovery musi ponownie respektować usunięcia
oraz opt-out; kopie mają własną retencję i klucz przechowywany oddzielnie.

## Źródła sprawdzone w tej sesji

HTTP 200, 2026-11-01, zapis dowodów w `documentation-evidence.json`:
- https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-unified-login/get-started
- https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-unified-login/permissions
- https://developers.facebook.com/documentation/instagram-platform/webhooks/setup
- https://render.com/docs/ssh

Potwierdzono ścieżkę/menu, scope, SUAT i identyfikatory, role/Standard/Advanced Access,
ograniczenie Live i business verification. Nie potwierdzono rzeczywistych ustawień
aplikacji właściciela, konta, tokenów, panelu Render ani działania Graph API.
