# Google Calendar — projekt integracji, bez aktywacji

## Co działa teraz

Lokalne appointments są źródłem prawdy. Google Calendar jest ręcznym formularzem,
nie połączeniem OAuth. GET /api/appointments/{id}/calendar-preview zwraca payload v3,
connected=false, external_write=false i requires_owner_approval=true.
Podgląd nie tworzy, nie aktualizuje i nie odwołuje wydarzenia Google.
Nawet anulowanie lokalnej wizyty nie usuwa wydarzenia dodanego ręcznie: użytkownik
musi osobno zmienić je w Google. Nie pokazujemy fikcyjnej synchronizacji.

## Kontrakt przyszłego adaptera (do implementacji)

1. OAuth Authorization Code + PKCE przez backend. Stan losowy, jednorazowy, krótki TTL,
   przypisany do bieżącej sesji managera; callback tylko dokładny HTTPS allowlist.
   Kod jednorazowy wymieniany serwerowo, brak tokenów/kodów w logach i API.
2. Minimalny zakres: calendar.app.created dla dedykowanego kalendarza tworzonego przez
   aplikację. Bez szerokiego calendar scope. Konflikty na prywatnych innych kalendarzach
   wymagają osobnej decyzji i ewentualnego calendar.freebusy; nie udawać ich widoczności.
   Oficjalne dokumenty do ponownej weryfikacji przy implementacji:
   https://developers.google.com/workspace/calendar/api/auth
   https://developers.google.com/identity/protocols/oauth2/web-server
3. Indywidualny grant/handlowiec i dedykowany kalendarz; przypisanie managera nie jest
   zgodą na działanie w cudzym koncie. Przechowywanie tokenów Fernet z oddzielnym
   GOOGLE_ENCRYPTION_KEY i kontrolą wersji klucza; nie rotować META_ENCRYPTION_KEY.
4. Każdy zapis wymaga zatwierdzonej lokalnej wersji wizyty przez managera, potwierdzonego
   kalendarza docelowego i zgody na zewnętrzną operację. Sam OAuth nie aktywuje zapisów.
   Transport domyślnie OFF, brak wysyłki zaproszeń uczestnikom (sendUpdates=none);
   adresy e-mail/telefony/notatki CRM nie trafiają automatycznie do payloadu.
5. Idempotentne event.id z calendar_preview. Obecne integration_links ma FK salon_id
   i unikalność provider/salon_id — nie nadaje się do wielu wydarzeń jednego salonu.
   Przyszła osobna tabela grantów i mapowań appointment/account/calendar/event/etag
   wymaga addytywnej migracji i testu przed osobnym zatwierdzonym wdrożeniem.
   Nie wykonano tej migracji i nie użyto tabeli Livespace jako atrapy kalendarza. ETag dla
   aktualizacji If-Match; konflikt 412 -> podgląd i decyzja człowieka, nie overwrite.
   409 po insert nie oznacza sukcesu: GET i zgodność private.focus3AppointmentId/docelowego konta.
6. Timeout/429/5xx -> bounded retry z backoff, brak fikcyjnego sent/synced. Stan zmienia się
   dopiero po potwierdzonej odpowiedzi API i zapisie mapowania/audytu. Kolejka outbox
   musi być odrębna od obecnych jobs analiz agenta; przed migracją test na kopii syntetycznej.
7. Webhooki/watch: oddzielna późniejsza zgoda, weryfikowany channel/token/resource ID,
   renew/syncToken/410-full-resync bez powielania wydarzeń. Nigdy automatyczne potwierdzenie
   klienta tylko dlatego, że wydarzenie istnieje w kalendarzu.
8. Rozłączenie unieważnia grant i czyści tokeny, blokuje zadania; nie usuwa lokalnych wizyt
   ani cudzych wydarzeń. Dane minimalne, retencja/audyt i zgodność opt-out.

Przyszłe nazwy sekretów: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI,
GOOGLE_ENCRYPTION_KEY. Żadnej z nich nie skonfigurowano. Żaden callback OAuth Google
nie został zaimplementowany ani zarejestrowany. Właściciel musi później zatwierdzić
projekt OAuth/consent i konto testowe w Google Cloud Console; nie prosimy o sekrety w czacie.
Testy bieżące dotyczą payloadu/ACL/braku HTTP, nie działania OAuth ani prawdziwego konta.
