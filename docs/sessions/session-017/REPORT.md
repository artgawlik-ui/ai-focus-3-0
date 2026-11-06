# RAPORT AI FOCUS — SESJA 017: natywny plan i monitoring kontaktów

## Decyzja i zakres

Właściciel w załączonym poleceniu wycofał dalszy rozwój Google Calendar. Sesję016
zamknięto raportem stanu, bez przypisywania jej niewykonanych testów. Wejście c754a36,
CI42132890378 SUCCESS/259, PR3 Draft potwierdzone. Google panel i ręczne linki kalendarza
wycofano z UI; kod API/testy/schemat005 i dane zachowane. Flagi Google nadal OFF w
przykładzie i nowym izolowanym E2E; nie czytano/zmieniano produkcyjnych zmiennych.

## Rzeczywiście zaimplementowane

FOCUS_CALENDAR_ENABLED=false domyślnie. Natywny panel na pulpicie, kalendarzu i w raportach:
- datowana lista klientów wymagających kontaktu, A+/A pierwsze; progi7/14/30/60 dni;
- indywidualny okres1–365 dni per salon oraz konfigurowalne okresy per priorytet/użytkownik;
- jawna ostatnia data kontaktu i źródłowy Activity.id; brak kontaktu jest NULL, osobno wiek
  od dodania. Dni kalendarzowe Europe/Warsaw, nie zaokrąglone okresy24h;
- rzeczywisty kontakt: zarejestrowane call/visit/email_received/instagram_received.
  Notatka, follow_up o niejednoznacznej semantyce, task, szkic i plan wizyty nie liczą się;
- trwałe zadania i przypomnienia w PostgreSQL; deduplikacja po salonie i wpisie kontaktu,
  wspólna blokada kontaktu z ponownym odczytem pod blokadą; GET nie generuje zapisów;
- zadania z terminem, priorytetem, statusem, wynikiem i powtarzaniem w lokalnej strefie;
  wersja przeciw nadpisaniu, odrzucenie identycznego zadania i ponownego wykonania;
- zakończenie zadania wymaga wyniku, ale nie jest kontaktem. Dopiero jawny wybór
  rodzaju rzeczywiście wykonanego kontaktu tworzy osobny wpis w historii CRM;
- zmiany zapisują Activity z użytkownikiem. Nowy kontakt unieważnia starsze automatyczne
  zadanie. Zakończone bez kontaktu nie resetuje licznika ani nie zalewa kolejnymi zadaniami
  tego samego cyklu; klient nadal jest w raporcie, można zaplanować osobne działanie;
- manager widzi zaniedbanych i zaległe zadania według opiekuna oraz jawne completed/on_time.
  Handlowiec wyłącznie aktualnie przypisane salony; opt-out wyklucza generowanie kontaktów;
- istniejący planer wizyt: dzień/tydzień + miesiąc, bez drugiego systemu appointments.
  Dotychczasowe konflikty, aktualizacja i anulowanie zachowane;
- istniejący worker co60s przygotowuje listy i wewnętrzne przypomnienia. Pauza i SIGTERM
  obejmują nowy etap, bez nowych usług/wątków/kosztów. Powiadomienia trwałe i deduplikowane;
  przypomnienia wizyt konfigurowalne, domyślnie1440/120/30min. Zmiana daty/anulowanie/
  przypisania filtruje nieaktualne przypomnienia. Panel odświeża się co60s.

## Schemat i rollback

Osobny NativeBase i native-alembic.ini, opcjonalne006 oparte na004. Cztery tabele:
focus_contact_policies, focus_work_settings, focus_tasks, focus_notifications.
Standardowe head004 nadal nie wymaga nowych tabel. Nowy profil nie wymaga Google005.
006 i005 są osobnymi opcjonalnymi ścieżkami; STOP jeśli trzeba przejść z istniejącego005
lub uruchomić oba profile. Nie wykonywać automatycznego downgrade005 ani łączenia głów.
Start odmawia obu flag schematu równocześnie. Plan produkcyjny wymaga świeżej kopii,
restore i zatwierdzenia. Downgrade006->004 tylko marker: nie kasuje danych/tabel.
Test lokalny porównuje fingerprinty danych przed/po re-upgrade i downgrade.
Po006 nie wyłączać flagi profilu przed osobno zatwierdzonym marker rollback; zwykły
profil004 nie zna006. Niczego nie wykonano na produkcji. ZgodaA nie rozszerzona.

## Testy i problemy

Nowe tests/test_native_planning.py:24 przypadki, lifecycle:1 dodatkowy etap.
Lokalny syntetyczny PostgreSQL17, portlocalhost55432, 256MB/1CPU, bez kopii klientów.
Komenda: DATABASE_URL=<synthetic focus3_test> pytest -q tests/test_native_planning.py
 tests/test_worker_lifecycle.py tests/test_visit_planner.py. Wynik końcowy: **55 passed,0failed,0skipped,30.15s**; wcześniejszy
zakres20+31 miał51 PASS/0FAIL. Nie sumować nakładających się zbiorów.
Pierwsza regresja ujawniła zasłonięcie nowych endpointów przez SPA: przeniesiono router.
Kolejne błędy fixture: dni liczone w UTC zamiast kalendarza Warszawy przy DST,
jednoznakowa niedozwolona nazwa salonu i nieuwzględnione automatyczne zadanie nowego leada.
Fixture poprawiono bez osłabiania właściwych zabezpieczeń. Dodano test anulowania starego
follow-up po kontakcie i przejęcia przypomnienia po zmianie opiekuna.
Build tsc/Vite, compileall i sh-n PASS. E2E Chromium/WebKit rozszerzone o natywny panel,
generowanie zadań i utworzenie własnego zadania. Google UI wycofano zgodnie z decyzją;
testy jednostkowe jego zabezpieczeń pozostają, bez prawdziwego API.
Pełne CI wymagane przed PASS kodu; wyniki/link w ChecksPR3 i raporcie porannym/komunikacie.

## Ograniczenia i dalsze zadania

Nie deklarujemy pełnej realizacji całego nowego zakresu: brak drag&drop, web push,
rozbudowanego kalendarza graficznego, pełnego raportu wykonanych/nieodbytych wizyt,
metryk opartych na zamówieniach i pełnego panelu edycji przypomnienia dla każdej wizyty.
Terminy zadań podaje się obecnie ISO ze strefą — wymaga ulepszenia ergonomii na telefonie.
Raport listy zadań limit1000, przypomnienia w przebiegu500; większa skala wymaga paginacji.
Nie ma automatycznej retencji nowych metadanych; polityka i test archiwizacji pozostają
otwarte. Powiadomienia wyłącznie wewnątrz aplikacji, nie push poza nią. Brak testu fizycznego
urządzenia dla nowego panelu. Nie wysłano żadnej wiadomości ani nie utworzono wydarzenia Google.

RPO60, bieżące SQL/integralność/konta004, magazyn/klucz i operacyjny rollback/handoff
nadal BLOCKED. Środowisko revision5, grantTCP pusty, bez powtarzania SSH/SQL. 0produkcyjnych
migracji/eksportów/restore/merge/deploy/config/Meta/DM/kosztów. Focus1/2 niezmienione.
Szacunek nadal co najmniej5 sesji podstawowych +≥1DM; nowy zakres nie zmniejsza bramek.
Następne zadanie: lepszy formularz terminu Warszawa, pełniejszy raport dnia/przypomnienia
oraz scenariusze awaryjne nowego workera. READY wyłącznie po końcowym zielonym CI kodu;
wdrożenie i pełna gotowość operacyjna BLOCKED.

## Potwierdzenie CI017

Commit ad348f0045529a6fa2170b54a69df4f3177d034f, workflow42302108082,
https://github.com/artgawlik-ui/ai-focus-3-0/actions/runs/42302108082: SUCCESS.
Backend284PASS, Chromium/WebKit PASS, build i audyty PASS,0 znanych podatności.
Kod017 PASS, produkcyjne wydanie nadal BLOCKED. Kontynuacja018 zgodnie z trybem nocnym.
