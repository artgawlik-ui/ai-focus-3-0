# Status weryfikacji — 2026-10-28

## Audyt istniejących zasobów (tylko odczyt)

- Konto GitHub: artgawlik-ui. Dostępne repo Focus-2.0, commit 945c335cc720cd46d2ff0732dc4c7a02e92bf0b9, zawiera lokalny prototyp SQLite i trzy fikcyjne salony.
- Render My Workspace: usługi ai-focus-2-0-app i ai-focus-2-0, obie wskazują inne repo artgawlik-ui/ai-focus-2-0. Próba odczytu tego repo zwraca 404.
- Istniejąca baza ai-focus-2-0-db: PostgreSQL 17, free, expiresAt 2026-11-24. Zapytanie read-only z narzędzia nie dotarło do bazy z powodu pustej allowlisty zewnętrznej. Konfiguracji nie zmieniano.
- Deklarowane 118 salonów: NIEZWERYFIKOWANE. Brak importu i brak kopiowania prywatnych danych klientów.
- Nie zmieniano repo, konfiguracji, usług ani danych Focus 1.0/2.0.

## Działające i przetestowane lokalnie

- Kompilacja React/TypeScript/Vite.
- 10 testów API na PostgreSQL 17: auth/CSRF/origin, właściciele i role, przypisanie opiekuna, duplikaty, konflikty wersji, import atomowy, eksport, terminy/trasy, agent/historia/zakaz kontaktu, KPI, limit logowania, bezpieczeństwo, szkolenia.
- Analogiczne testy SQLite dla podstawowego trybu lokalnego.
- Chromium desktop 1440px i mobilny 390px: logowanie, pulpit, profil, zapis salonu, brak poziomego przewijania, manifest i ikony. Syntetyczne dane, bez danych produkcyjnych.
- Oddzielny worker przetwarza kolejkę testową; szkic nigdy nie otrzymuje statusu wysłanego.
- PostgreSQL backup AES-GCM/pg_dump → osobna baza → zgodność liczebności i skrótów tabel.
- Blueprint przechodzi aktualny publiczny JSON Schema Render. CLI jest zainstalowane, platformowa walidacja wymaga autoryzacji.

## Przygotowane lub wymagające dalszej weryfikacji

- OpenStreetMap: kod odpytywania publicznych salonów z ograniczonym zapytaniem i jawnym źródłem; wynik zależy od dostępności Overpass. Brak gwarancji pełności danych.
- Model OpenAI: adapter, bez aktywowanego sekretu i bez zgody na płatne wywołania.
- Google Calendar: ręczne dodawanie linkiem; OAuth i synchronizacja niepodłączone.
- Livespace: wyłącznie schemat mapowania tożsamości; brak synchronizacji sieciowej.
- Instagram: brak autoryzacji i wysyłki.
- Safari/WebKit: przeglądarka pobrana, uruchomienie zablokowane brakującymi bibliotekami systemowymi. Test mobilny Chromium nie jest testem Safari ani instalacji na fizycznym iPhonie.
- Backup offsite, harmonogram, alerty i retencja: nieskonfigurowane.
- E-mail/push przypomnienia, optymalizacja tras, reset hasła e-mail/MFA: niewdrożone.

## Publikacja i produkcja

Koszt około 20 USD/mies. za nowe Render web + worker + PostgreSQL zatwierdzony w rozmowie. Płatne AI wyłączone. Dostęp do nowego repo i autoryzacja Render CLI są sprawdzane przed wdrożeniem. Nie traktować lokalnej weryfikacji jako dowodu działania HTTPS lub trwałości danych na Render.
