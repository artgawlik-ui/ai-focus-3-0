# Ai Focus 3.0

Aktualny punkt wznowienia i ograniczenia wydania: [RESUME.md](RESUME.md). Ostatni odczyt produkcji w sesji 012 potwierdził d15265b (3.0.3); kandydat 3.0.4 pozostaje w Draft PR #3, bez deployu. Raport Meta: [docs/meta/REPORT.md](docs/meta/REPORT.md).

Osobny CRM sprzedaży NAK Hair / muk Haircare. React 19 + TypeScript, FastAPI, SQLAlchemy, PostgreSQL 17, Alembic. Polskie UI, responsywna PWA, indywidualne konta menedżera i handlowców. Bez automatycznej wysyłki wiadomości.

## Funkcje zaimplementowane

- CRM: profile, kontakt, Instagram, obszar, priorytety, etapy, potencjał miesięczny, notatki, daty ponownego kontaktu, historia i przypisywanie opiekuna.
- Sesje HttpOnly/SameSite, CSRF, kontrola właściciela salonu, konta zespołu, Argon2, ograniczenie prób logowania, zmiana hasła przez API.
- Excel: eksport, podgląd importu, transakcyjny zapis bez częściowego importu, wykrywanie duplikatów nazwa/miasto, limity rozmiaru, ochrona przed formułami.
- Agent: trwała kolejka PostgreSQL, osobny proces, analiza historii, kontrola niedawnego kontaktu i zakazu kontaktu, szkice. Domyślnie reguły; opcjonalny adapter modelu OpenAI wymaga konfiguracji i osobnej zgody na koszty. Żadnej wysyłki.
- Odkrywanie salonów: publiczny serwis Overpass/OpenStreetMap, jawne źródła, ręczna weryfikacja i dodanie do CRM. Dostępność i kompletność zależy od zewnętrznego serwisu.
- Kalendarz: propozycje i potwierdzenia, wykrywanie kolizji, historia wizyt, ręczny link Google Calendar, Google Maps w kolejności godzin.
- Raporty: lejek aktualnego stanu, aktywności dzienne/tygodniowe/miesięczne, KPI zespołu, potencjał, orientacyjna prognoza ważona i konwersja. Brak udawanych danych o przychodach.
- Planowanie szkoleń zespołu przez menedżera.
- PWA: manifest, ikony, widok mobilny, ekran offline. CRM wymaga połączenia; dane prywatne nie są cache'owane.
- Szyfrowane kopie `pg_dump`, odtworzenie wyłącznie do pustej bazy i porównanie skrótów zawartości.

## Lokalnie

Python 3.12, Node 22; PostgreSQL 17 zalecany. SQLite służy wyłącznie do lokalnych testów.

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt pytest
npm ci --prefix frontend
npm run build --prefix frontend
alembic upgrade head
# Ustaw BOOTSTRAP_EMAIL i BOOTSTRAP_PASSWORD przez bezpieczne zmienne środowiska.
python -m scripts.bootstrap
sh scripts/start.sh
# start.sh uruchamia supervisor, API i worker; nie uruchamiaj drugiego workera.
```

Nie uruchamiaj seedera na produkcji. `scripts/seed_test.py` wymaga `APP_ENV=test` i pustej bazy. Testy API odmawiają pracy na bazie innej niż jawnie wskazana baza testowa.

```sh
pytest -q
# PostgreSQL, wyłącznie izolowana baza focus3_test:
DATABASE_URL=postgresql://postgres@127.0.0.1:55432/focus3_test pytest -q
# Uruchomiona aplikacja z syntetycznymi danymi E2E na porcie 8001:
python tests/browser_check.py
```

API: `/docs`; gotowość: `/api/health`.

## Render

`render.yaml` definiuje usługę `ai-focus-3-0` we Frankfurcie i odwołuje się do już istniejącej, odizolowanej bazy `ai-focus-3-0-db`. API i agent to osobne procesy nadzorowane w jednej usłudze. Zatwierdzony koszt bazowy: około 13 USD/mies. (7 web + 6 PostgreSQL), bez dodatkowego zużycia i podatków. Nie twórz drugiej bazy ani nie zmieniaj Focus 1.0/2.0.

Blueprint generuje hasło początkowego konta w bezpiecznym środowisku Render. Nie ma hasła domyślnego; wartości nie wolno publikować w repozytorium ani wiadomości. Konto techniczne zostało wyłączone. Właściciel może odczytać początkowy sekret w oficjalnym panelu Render i zmienić hasło w aplikacji. Produkcja wymaga PostgreSQL; SQLite jest odrzucane.

`APP_ORIGIN` musi odpowiadać rzeczywistemu adresowi HTTPS. PostgreSQL ma pustą listę dostępu zewnętrznego i komunikuje się z nowymi usługami w sieci prywatnej. Worker ponawia połączenie podczas migracji bazy. Sygnał SIGTERM kończy pętlę po bieżącym zadaniu; przerwane zadanie można odzyskać po 5 minutach.

## Granice integracji

- Google Calendar: działa ręczne otwieranie formularza, brak OAuth i synchronizacji dwukierunkowej.
- Instagram: adapter Unified Login i podpisane webhooki wdrożone za wyłącznikiem; rzeczywista autoryzacja konta testowego czeka na właściciela. Brak transportu wysyłki.
- Livespace: przygotowana tabela mapowania zewnętrznych ID/kursora z unikalnością; brak aktywnej synchronizacji i adaptera sieciowego. Wymaga uzgodnienia źródła prawdy i API.
- OpenAI: adapter przygotowany, domyślnie nieaktywny, brak testu realnego modelu bez autoryzowanego sekretu i zgody kosztowej.
- Planowanie trasy: kolejność godzin, nie optymalizacja odległości ani ruchu.
- Przypomnienia: lista ponownych kontaktów w pulpicie; brak push i wysyłki e-mail.
- Konta: tworzenie i zmiana własnego hasła, bez samoobsługowego resetu e-mail/MFA i bez panelu dezaktywacji.

Szczegóły testów i blokad: [docs/STATUS.md](docs/STATUS.md). Odtwarzanie: [docs/RECOVERY.md](docs/RECOVERY.md).

## Wyszukiwanie miejscowości i promienia (kandydat 013)

`DISCOVERY_RADIUS_ENABLED=false` domyślnie zachowuje dotychczasowe wyszukiwanie miasta.
Po osobnej aktywacji dostępne są wybór centrum miejscowości w Polsce i promień 1–50 km,
odległości w linii prostej, źródła OSM i czas odczytu. Dodanie do CRM wymaga formularza
weryfikacji; brakujące dane pozostają puste. Geokodowanie wysyła tylko wpisaną miejscowość,
nie dane CRM. Nominatim jest wywoływany przyciskiem (bez autocomplete), z User-Agent,
cache do 128 miejscowości/24 h i limitem 1 żądania/s współdzielonym przez PostgreSQL.
Krótka transakcja geokodowania zajmuje połączenie do 10 s; kolejne równoległe żądania
są odrzucane 429 zamiast kolejkowane. Nie włączać na innym backendzie bazy bez analizy limitu.
`GEOCODING_SEARCH_URL` pozwala operatorowi zmienić kompatybilną usługę bez aktualizacji kodu;
tylko HTTPS bez sekretów w URL i bez przekierowań. Zmiana produkcyjna wymaga zgody.
Źródła są niekompletne, wyniki ograniczone do 100; brak wyniku nie oznacza braku salonów.
Publiczny serwis nie ma gwarancji dostępności. Polityka sprawdzona 5 listopada 2026:
https://operations.osmfoundation.org/policies/nominatim/ (HTTP 200). Brak nowych płatnych usług.

## Plan wizyt (kandydat sesji 014)

`VISIT_PLANNER_ENABLED=false` domyślnie. Po zatwierdzonej aktywacji: dzień/tydzień
Europe/Warsaw, filtr handlowca dla managera, propozycja domyślnie 20 min w formularzu,
zmiana terminu/notatek/statusu i odwołanie. CRM jest źródłem prawdy. Nowy workflow
pozwala handlowcowi proponować, a potwierdzenie wymaga managera i jawnej deklaracji,
że klient uzgodnił termin. Brak automatycznych wydarzeń, wiadomości i potwierdzeń.
`calendar-preview` to wyłącznie payload przyszłego adaptera, nie OAuth ani synchronizacja.
Nawigacja i lokalizacja Google wymagają ręcznej weryfikacji aktualnego adresu w profilu;
zmiana profilu unieważnia weryfikację. Zabezpieczenie tras działa również przy fladze OFF.
Projekt integracji: [GOOGLE_CALENDAR_PLAN.md](docs/integrations/GOOGLE_CALENDAR_PLAN.md).
