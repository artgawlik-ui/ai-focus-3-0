> Decyzja właściciela 2026-11-06: integracja Google wycofana z dalszego rozwoju.
> Poniższy dokument jest historycznym opisem kodu015. Flagi pozostają OFF;
> kod/tabele/historia zachowane bez destrukcyjnego rollbacku. Nowy kierunek: natywny Focus.

# Google Calendar — implementacja 015, integracja na żywo nieaktywna

## Zakres

Lokalne appointments są źródłem prawdy. Zachowany ręczny formularz i stary
`/appointments/{id}/calendar-preview` nie oznaczają synchronizacji. Nowy panel
`GoogleCalendarPanel` i API `/api/google-calendar` obsługują osobny, opcjonalny adapter.
Kod i mocki: zaimplementowane. Rzeczywisty grant, konto i operacje Google: niezweryfikowane.

- OAuth każdego zalogowanego użytkownika: state związany z sesją, TTL 5 min, S256 PKCE,
  kod jednokrotny, wymiana POST na backendzie. Ponowne połączenie wymaga nowego
  zatwierdzenia managera. Disconnect unieważnia również trwający lokalny OAuth.
- Jedyny scope: `https://www.googleapis.com/auth/calendar.app.created`.
  Osobny, nowy kalendarz aplikacji; brak dostępu do primary i prywatnych innych kalendarzy.
  Nie ma freebusy innych kalendarzy. Lokalny planer nadal sprawdza lokalne kolizje.
- Tokeny i zatwierdzone payloady Fernet, osobny klucz Google. Nie rotowano klucza Meta.
  Refresh pod blokadą konta; timeout/429/5xx nie kasują poprawnego grantu.
- Manager zatwierdza konto, utworzenie kalendarza i konkretny podgląd wersji wizyty.
  Handlowiec może połączyć/rozłączyć wyłącznie własny grant. Potwierdzenie w CRM nie
  uruchamia synchronizacji samoistnie. Każda nowa wersja wymaga nowego zatwierdzenia.
- Kolejka trwała, ID wydarzenia deterministyczny, GET przed insert, obsługa 409 i ETag/412.
  Zmiana CRM/opt-out/przypisania/aktywności/grantu po zatwierdzeniu blokuje stare zlecenie.
  Retry maksymalnie 5 prób, backoff do 300 s, ważność zatwierdzenia 15 min.
  Niepewny wynik utworzenia samego kalendarza wymaga ręcznej weryfikacji, bez ponowienia.
- Anulowanie: PATCH status=cancelled, nigdy DELETE. Brak zaproszeń i adresów odbiorców;
  `sendUpdates=none`. Do Google trafia minimum nazwy/terminu i zweryfikowany adres,
  bez telefonu, e-maila i notatek CRM. Audyt Activity dopiero po potwierdzonym API.
- Disconnect usuwa lokalne tokeny i blokuje oczekujące zlecenia; zachowuje mapowania,
  historię oraz wizyty. **Nie odwołuje grantu w Google**: właściciel konta usuwa dostęp
  w ustawieniach bezpieczeństwa Google. Nie usuwa istniejących wydarzeń.

## Konfiguracja — niczego nie ustawiono na produkcji

Wszystkie flagi domyślnie false, tylko wartość `true` (bez względu na wielkość liter)
ją włącza; brak/pusta/niepoprawna wartość pozostaje false.

| Zmienna | Znaczenie |
|---|---|
| GOOGLE_SCHEMA_ENABLED | Wybiera opcjonalny profil migracji 005 i dostęp do tabel Google |
| GOOGLE_CALENDAR_ENABLED | OAuth i panel połączenia, wymaga schematu |
| GOOGLE_CALENDAR_WRITE_ENABLED | Niezależna blokada transportu zapisów i pracy workera |
| GOOGLE_CLIENT_ID | Identyfikator klienta Web OAuth |
| GOOGLE_CLIENT_SECRET | Sekret klienta, wyłącznie konfiguracja bezpieczna |
| GOOGLE_REDIRECT_URI | Dokładny callback, identyczny w obu krokach OAuth |
| GOOGLE_ENCRYPTION_KEY | Fernet: 44 znaki URL-safe base64 reprezentujące 32 bajty |

Callback do późniejszej rejestracji: `https://ai-focus-3-0.onrender.com/api/google-calendar/oauth/callback`.
Nie dodawać ukośnika na końcu. APP_ORIGIN musi odpowiadać tej samej domenie HTTPS.
Nowe tabele: google_oauth_states, google_accounts, google_event_links, google_sync_requests.
Standardowe `alembic upgrade head` pozostaje 004/17 tabel. Profil Google:
`alembic -c google-alembic.ini upgrade head` daje 005/21 tabel na syntetycznej bazie.

## Wdrożenie i rollback — wyłącznie propozycja

STOP bez świeżej zaszyfrowanej kopii, testu restore, klucza poza serwerem, integralności,
RPO ≤60 min, kontrolowanego drain starych workerów oraz zgody na migrację/deploy.
Po osobnej zgodzie: pauza workera, kopia/test, migracja sprawdzona wcześniej na kopii,
005, wdrożenie z enabled=false/write=false. Po kontroli 21 tabel i kont dopiero decyzja
właściciela o OAuth na kontach testowych. Dotychczasowa zgoda A na 4 SELECT-y/17 tabel
nie obejmuje nowego manifestu 21 tabel — nie zmieniono jej zapytań.

Po 005 zachować GOOGLE_SCHEMA_ENABLED=true także przy wyłączeniu integracji; zwykły
profil 004 nie zna rewizji 005. Cofnięcie kodu wymaga osobno zatwierdzonego
`alembic -c google-alembic.ini downgrade 004`: zmienia wyłącznie marker, zachowuje
wszystkie cztery tabele i ich dane. Test porównuje fingerprinty 20 tabel danych.
Nie uruchamiać starego workera bez procedury drain/fencing/retencji z sesji 011–012.
Ponowne upgrade 005 jest idempotentne. Brak automatycznego DROP tabel lub tokenów.

## Oficjalne wymagania — sprawdzono 2026-11-05

- https://developers.google.com/workspace/calendar/api/auth — minimalny scope app.created.
- https://developers.google.com/identity/protocols/oauth2/web-server — authorization code,
  offline/refresh, redirect URI i serwerowa wymiana tokenu POST.
- https://developers.google.com/identity/protocols/oauth2/native-app — PKCE/S256.
- https://accounts.google.com/.well-known/openid-configuration — serwer reklamuje S256.
  Dokument Web OAuth nie opisuje PKCE wprost: kompatybilność z zarejestrowanym klientem
  Web i odrzucenie złego verifier wymagają testu właściciela przed aktywacją. Bez fallbacku.
- https://developers.google.com/workspace/calendar/api/v3/reference/calendars/insert —
  tworzenie nowego kalendarza ze scope app.created; API Calendar v3.
- https://developers.google.com/workspace/calendar/api/guides/create-events — sendUpdates.
- https://developers.google.com/workspace/calendar/api/guides/version-resources — ETag/If-Match.

Właściciel później: Google Cloud Console → APIs & Services → Enable APIs → Calendar API;
Google Auth Platform → Audience (Testing/test users), Data Access (wyłącznie app.created),
Clients → Web application → Authorized redirect URIs (powyższy callback).
Wartości sekretów wyłącznie w bezpiecznych ustawieniach, nigdy w rozmowie/repozytorium.
Tryb Live/weryfikacja aplikacji zależą od zakresu i odbiorców, nie są tu zatwierdzone.

## Ograniczenia

Brak rzeczywistego OAuth, testu PKCE z kontem Web, event API i odwołania grantu Google.
Brak watch/webhook/syncToken, pełnej synchronizacji zmian ręcznych i nadpisania konfliktów.
Zewnętrzny efekt HTTP i commit PostgreSQL nie są atomowe: deterministyczny ID i odczyt
po retry ograniczają duplikaty wydarzeń, ale nie gwarantują exactly-once HTTP.
Worker używa istniejącego procesu i puli, bez SDK/Redis/nowej usługi; timeout HTTP 10 s,
jedno zlecenie na przebieg, pauza/stop sprawdzane między etapami. Blokady podczas HTTP
mogą opóźnić edycję tej wizyty; restart odzyskuje transakcję i sprawdza ID wydarzenia.
Historia zleceń zawiera metadane; payload szyfrowany i czyszczony w stanach końcowych.
Automatyczna retencja nowych metadanych OAuth/sync wymaga osobnego harmonogramu/polityki;
nie uruchomiono cleanup. Brak nowych zasobów/kosztów, limitów użycia na żywo nie badano.
