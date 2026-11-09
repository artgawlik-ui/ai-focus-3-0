# RAPORT AI FOCUS 3.0.4 — SESJA 014

## Punkt wejściowy i zachowany zakres

HEAD lokalny/GitHub 913821549837365b637aebe29a5c5e2549ad05f0 zgodny, CI 42094884611
success, 209 testów; PR #3 Draft. Odczytano RESUME, raport 013, RELEASE_GATE i kod
CRM/appointments/routes. Poprawki 008–013 i prywatne nieśledzone archiwa zachowane.
Nie powtarzano ich pełnych testów bez powodu; nowa regresja wynika ze zmian wizyt.

## Faktycznie zaimplementowane

Rozszerzono istniejące appointments, bez nowej tabeli i bez migracji (nadal 004):

- GET /appointments: data + 1/7 dni, granice Europe/Warsaw/DST, filtr representative_id;
  handlowiec widzi własne przypisane salony/wizyty, manager może wybrać członka zespołu.
- PATCH /appointments/{id}: zmiana terminu, długości, notatek i statusu. Blokada handlowca
  serializuje rezerwacje; wiersz wizyty odczytywany ponownie pod blokadą. Revision SHA
  pól wizyty pozwala odrzucić stary formularz (409), także przy równoległej zmianie notatki.
- Proponowane i potwierdzone sloty blokują kalendarz; duplikat/kolizja ->409. Anulowanie
  zwalnia slot. Datetime bez strefy/minuty poza limitem ->422. Historię zapisuje Activity
  w tej samej transakcji co wizyta. Nie kasuje się rekordów klientów ani historii.
- Nowy UI: dzień/tydzień od poniedziałku, filtr handlowca, karta z profilem/historią,
  propozycja 20 min (dopuszcza 15–480), zmiana/odwołanie. API zachowuje dotychczasowy
  domyślny czas 45 min dla zgodności; nowy formularz ustawia 20 min.
- W nowym workflow status confirmed wymaga roli manager i confirmation_recorded=true;
  to jawna deklaracja użytkownika o uzgodnieniu z klientem, nie dowód z API klienta.
  Nie tworzy się fikcyjnych automatycznych potwierdzeń. Przy fladze OFF zachowano
  dotychczasową semantykę statusów API. Nowe propozycje respektują status/Meta opt-out.
- VISIT_PLANNER_ENABLED=false domyślnie: ukrywa nowy panel i blokuje zmianę terminu/notatek.
  Nie zmieniono rzeczywistych flag środowiskowych. Odczyt/podgląd i bezpieczeństwo adresu
  są addytywnymi zabezpieczeniami niezależnymi od włączenia panelu.

## Adres i nawigacja

POST /salons/{id}/verify-address wymaga sesji, CSRF, praw do salonu i zgodności
przesłanego adresu/miasta z aktualnym profilem. Pod wspólną blokadą kontaktu zapisuje
Activity address_verified. Jest to ręczna weryfikacja przez użytkownika, nie geokoder.
Nawigacja/Google location powstają tylko przy zgodnym adresie i potwierdzeniu nie starszym
niż updated_at profilu. Zmiana profilu (także opiekuna) unieważnia potwierdzenie.
Nie pozwolono wstrzykiwać kind=address_verified przez ogólne API notatek.
Trasy obejmują tylko confirmed + verified. Manager nie dostaje jednej trasy łączącej
różnych przedstawicieli; musi wybrać representative_id. Nadal kolejność godzin,
bez optymalizacji drogi lub ruchu. Lokalna nawigacja nie potwierdza odbycia wizyty.
To celowe zaostrzenie starego zachowania: sam wpisany adres już nie wystarcza.

## Google Calendar — co przygotowano, czego nie ma

Ręczny formularz Google jest zachowany i oznaczony bez synchronizacji. Bez zweryfikowanego
adresu formularz nie dostaje location. Lokalne odwołanie nie odwołuje wydarzenia dodanego
ręcznie w Google — potrzebna osobna czynność użytkownika.
GET /appointments/{id}/calendar-preview zwraca connected=false, external_write=false,
requires_owner_approval=true oraz minimalny payload v3. ID stabilne, status tentative dla
propozycji, brak adresu bez weryfikacji, brak e-maili/telefonów/notatek w payloadzie.
Nie ma transportu HTTP Google, callbacku OAuth, tokenów, watch ani aktywnej synchronizacji.
Architektura opisana w docs/integrations/GOOGLE_CALENDAR_PLAN.md: sesyjny state/PKCE,
minimalny calendar.app.created i dedykowany kalendarz, osobna zgoda na freebusy innych
kalendarzy, Fernet, idempotencja/ETag, outbox, potwierdzenie odpowiedzi API i rozłączenie.
Obecne integration_links jest salonowe i nie nadaje się do wielu wydarzeń; przyszłe
mapowanie wymaga osobnej addytywnej migracji/testu. Nie zrobiono atrapy takiej tabeli.
Wymagania OAuth trzeba zweryfikować w oficjalnych dokumentach przed implementacją.
Nie połączono kont Google ani nie utworzono/zmieniono prawdziwych wydarzeń.

## Testy i dowody

Nowe tests/test_visit_planner.py: **16 przypadków**. Syntetyczny PostgreSQL 17,
256 MB/1 CPU, lokalny port 55432; brak kopii produkcji i realnych kontaktów.
- `pytest -q tests/test_visit_planner.py tests/test_api.py tests/test_contact_concurrency.py`:
  33/33 PASS, po dodaniu rozdzielenia uprawnień 34/34 PASS (18.83 s).
- Po dodaniu oddzielania tras przedstawicieli `pytest -q tests/test_visit_planner.py`:
  **16 passed, 0 failed/skipped, 11.14 s**. Zbiory nakładają się, nie sumować.
- RBAC, podwójne równoległe zgłoszenie (1x201/1x409), konflikty/reaktywacja, anulowanie,
  stale revision, opt-out, jawna zgoda managera, DST, preview/stabilny ID/brak HTTP,
  unieważnienie adresu i brak trasy z niepotwierdzonego adresu, rozdzielenie zespołu.
- `npm run build --prefix frontend` PASS. `compileall`, `git diff --check`, `pip check` PASS.
- Ostatnie uchwyty testów sprzed wznowienia nie były dostępne (Unknown process id).
  Nie uznano ich wyniku za PASS; ponowiono odpowiedni zestaw w istniejącej syntetycznej bazie.
- E2E dodany do istniejących Chromium/WebKit: znaleziony salon -> CRM -> plan dnia,
  propozycja 20 min -> historia -> ręcznie potwierdzony adres -> zmiana 15 min/terminu,
  jawne potwierdzenie managera -> anulowanie -> tydzień/filtr handlowca/brak overflow.
  VISIT_PLANNER_ENABLED=true tylko w izolowanym serwerze testowym. Brak kliknięć
  uruchamiających nawigację lub rzeczywisty formularz wydarzenia w Google.
- Końcowy CI dokładnego SHA musi być success przed PASS kodu; wynik w Checks PR #3
  i raporcie rozmowy. Emulacja WebKit nie jest fizycznym iPhonem.

## Rollback i pozostałe blokady

Brak zmiany modeli/migracji. Wyłączenie VISIT_PLANNER_ENABLED przywraca stary panel,
blokuje zmianę terminu, zachowuje dane i bezpieczeństwo weryfikacji adresu w nowym kodzie.
Powrót całego kodu do d15265b traci nowe zabezpieczenia adresów/pauzy/opt-out/fencing:
nie zakładać ich działania po rollbacku. Obowiązuje kontrolowany drain i osobne zatwierdzenie.
Macierz dowodów produkcyjnych 013 nadal aktualna: brak aktualnego SQL/kont/17 SHA,
RPO60, trwałego magazynu/klucza, eligibility/env rollbacku i produkcyjnego handoffu.
Środowisko nadal revision 5, current/running/connected, capabilities puste. Nie pojawił
się nowy kanał lub setter grantu. Zgodnie z instrukcją nie powtarzano kontroli TCP ani SSH.
**0 SELECT-ów produkcyjnych, 0 SSH.** Zgoda A aktualna; nie prosić ponownie.
Najbliższa czynność operacyjna właściciela: aktywować ograniczony grant Codex do
ssh.frankfurt.render.com:22; nie zmieniać allowlisty PostgreSQL. Potem zaufany host,
autoryzacja, prywatne ID i wyłącznie 4 zatwierdzone SELECT-y.

## Zapis i szacunek

Pliki: backend/main.py, schemas.py, visit_planner.py, calendar_preview.py;
frontend/src/main.tsx i VisitPlanner.tsx; tests/test_visit_planner.py, test_api.py,
ci_e2e.py i production_browser_check.py; .env.example, README.md, RESUME.md,
docs/integrations/GOOGLE_CALENDAR_PLAN.md i dokumenty 014.
SHA: `git log -1 --format=%H -- docs/sessions/session-014/REPORT.md`.
PR pozostaje Draft, bez merge/deploy/produkcyjnych migracji/restore/PITR/eksportów,
zmian sekretów/sieci/Render/Meta i realnych DM. Nowe koszty: 0. Focus 1.0/2.0 nietknięte.
**Wydanie operacyjne BLOCKED. Szacunek nadal 5 sesji podstawowych + ≥1 DM**;
nowa funkcja nie zamyka wymagań produkcyjnego recovery/dostępu, brak podstaw do redukcji.

## Korekta po pierwszym CI

CI 2b8e16e (42123531272): backend/build PASS, E2E zatrzymało się na dokładnym
selektorze label=Status w formularzu zmiany. Wcześniejsze kroki propozycji/historii
i potwierdzenia adresu/nawigacji wykonane. Dodano jednoznaczne aria-label=Status wizyty
oraz jawne etykiety ARIA filtrów planu. Test nadal wykonuje potwierdzenie/anulowanie;
nie usunięto kroku ani nie zwiększano timeoutu. Końcowe CI nowego SHA wymagane osobno.
