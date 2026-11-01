# Release gate 3.0.4 — przygotowanie READY, wykonanie BLOCKED

Ta lista zastępuje historyczne założenia o bieżącej produkcji. Nie wykonano czynności
produkcyjnych. Odniesienie kodu bazowego a9e2fab: obie kontrole CI PASS sprawdzone ponownie.
Aktualny kandydat to HEAD gałęzi fix/3.0.4-meta-validation; przed decyzją odczytać jego SHA
oraz wszystkie checks, nie zastępować ich wynikiem starszego commita.

## Warunki przed osobnym zatwierdzeniem

- [ ] Zgoda na odczytowy kanał istniejącej usługi; potwierdzony SSH/Shell i grant TCP.
- [ ] Preflight READ ONLY bieżącej bazy: schema 004, zgodność manifestu oraz każdej zależności.
  Historyczny zakres to 13 rekordów; nie potwierdzamy go jako stanu aktualnego.
- [ ] Bieżąca tożsamość właściciela i konta technicznego jednoznaczna; techniczne active=false
  i brak sesji; właściciel aktywny oraz osobny potwierdzony test logowania właściciela.
  Nie wyłączać konta w tej sesji: taka zmiana to osobna operacja produkcyjna.
- [ ] Świeża zaszyfrowana kopia PostgreSQL oraz test odtworzenia na kopii: wszystkie count/SHA,
  schemat/ograniczenia/indeksy, miejsce trwałego przechowywania i niezależny klucz.
  Lokalne dowody sesji 001 potwierdzają procedurę, nie świeżość kopii produkcji.
- [ ] Celowany undo cleanup zaszyfrowany poza repo, przypisany do tej samej kopii i zakresu;
  odtworzenie przetestowane. Trwałość historycznych plików/klucza poza sesją NIEZWERYFIKOWANA.
- [ ] Osobna decyzja o cleanup: obecna gałąź nie wykonuje DELETE/COMMIT produkcji.
  Sam cleanup nie jest warunkiem działania CRM; jest odrębną zatwierdzaną operacją.
- [ ] Aktualne testy/backend/build/Chromium/WebKit i audyty zielone; bez użycia realnego Meta.
- [ ] Wszystkie flagi Meta sprawdzone osobno i efektywnie OFF, DM niezależnie OFF;
  brak niejawnego dziedziczenia true z legacy. Nie zmieniać ich w tej sesji.
- [ ] Kod i Alembic: jedyny head 004, brak nowej migracji w tej sesji. Każda przyszła migracja
  dopiero po teście na kopii, bez automatycznego destrukcyjnego downgrade.
- [ ] Odczytany rzeczywisty działający commit/deploy do rollbacku; d15265b jest jedynie
  historycznym kandydatem, nie świeżym potwierdzeniem dostępności obrazu.
- [ ] Właściciel zatwierdza merge i deploy oddzielnie. W tej sesji oba zabronione.

## Smoke po przyszłym zatwierdzonym wdrożeniu

Tylko po osobnej zgodzie: health/readiness, HTTPS, commit faktycznie uruchomiony,
prywatne API bez sesji 401, owner login/logout, Meta OAuth/webhook/ingest/DM OFF,
przegląd logów bez query/tokenów. Nie testować zapisów na rzeczywistych salonach.
Przed/po redeployu porównać wszystkie count/SHA przy zatwierdzonym oknie bez zapisów,
READ ONLY snapshotach i niezmienionym schemacie. `scripts/data_release_gate.py`
odrzuca brak tabel, różne hashe/liczności i niepoprawny manifest.
Nie ignorować naturalnych zmian sesji/jobów — wymagają jawnego wyjaśnienia i osobnego
kontrolowanego okna; bez tego pełna niezmienność nie jest potwierdzona.
Procedura technicznego konta unieważnia wszystkie sesje; nie odtwarzać starej aktywnej
sesji przez rollback aplikacji/DB. Stan produkcyjny pozostaje BLOCKED do wykonania.

## Plan wycofania (wyłącznie propozycja)

Cel: wrócić do zatwierdzonego, faktycznie dostępnego deployu bez utraty danych.
Kroki: wstrzymać dalsze zmiany -> zachować snapshot/diagnostykę -> Meta OFF po zgodzie
-> rollback aplikacji do uprzednio zapisanego commita/deployu -> smoke i kontrola danych.
Nie wykonywać DROP, nie nadpisywać bazy i nie kasować inboxa; sesja 002 nie dodaje schematu.
Nieznany stan backupu/deployu albo rozbieżne hashe zatrzymują operację.
Ryzyko: nieaktualna kopia, niezgodność schematu poprzedniego kodu, aktywacja starych sesji.
Warunek: poprzedni kod zna revision 004 i odczyta istniejące dane; test zgodności na kopii.
Cleanup ma osobny transakcyjny ROLLBACK/undo, nie łączyć go z deployment rollback.
