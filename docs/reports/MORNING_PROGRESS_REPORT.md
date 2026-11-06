# Raport postępu — 2026-11-06, Europe/Warsaw

## Aktualny stan

Sesja016 zamknięta po decyzji właściciela o rezygnacji z Google. Sesja017 i018 ukończone,
019: implementacja i testy lokalne ukończone, pełny CI bieżącego HEAD do potwierdzenia.
PR3 pozostaje Draft: https://github.com/artgawlik-ui/ai-focus-3-0/pull/3.
Nie ma działania w tle po zakończeniu bieżącego wykonania. RESUME zawiera plan wznowienia.

## Dodane funkcje

Natywny planer dzień/tydzień/miesiąc wykorzystuje dotychczasowe appointments.
Monitoring rzeczywistych kontaktów, progi7/14/30/60, indywidualny okres klienta i per
priorytet, A+/A pierwsze, brak zarejestrowanego kontaktu odróżniony od wieku rekordu.
Trwałe, deduplikowane zadania z wynikiem, powtarzaniem i priorytetem; osobne jawne
potwierdzenie kontaktu. Raporty dnia, okna2h/24h, jawne ryzyko do2h, manager/handlowiec,
zaległości/terminowość i odnotowane zakończenia wizyt. Nie zakładamy odbycia spotkania.
Konfigurowalne przypomnienia wewnętrzne, centrum powiadomień, odczyt ustawień,
aktualizacja opiekuna i unieważnianie nieaktualnych przypomnień. Brak push.
Datetime-local Warszawa z walidacją luki i dwuznacznościDST; blokady salonu/opt-out,
rewizje zadań, brak zaliczania szkicu lub planu do rzeczywistych kontaktów.
Google kod/tabele005 zachowane, panel i linki kalendarza wycofane; bez OAuth/API live.

## Testy, commity i dowody

-017: ad348f0045529a6fa2170b54a69df4f3177d034f, CI42302108082 SUCCESS/284PASS,
 Chromium/WebKit/build/audytyPASS,0 znanych podatności. Lokalnie55PASS.
-018: 8c64fa0ec9189aa95d8e14929f0106f6ede1e649, CI42303042647 SUCCESS/293PASS,
 Chromium/WebKit/build/audytyPASS,0 znanych podatności. Lokalnie48PASS.
-019: lokalnie68PASS/0failed/0skipped/34.13s; build/compile/diffPASS. Nowe4 testy,
 łącznie38 nowych przypadków od015 (25+9+4). Nie sumować lokalnych nakładających się zbiorów.
 E2E rozszerzone: zadanie->jawnykontakt->nowa data->zmiana okresu klienta, oba silniki.
 Końcowy SHA i CI: ChecksPR3 / git log -1 -- docs/sessions/session-019/REPORT.md.
Prywatne ZIP-y zachowane pozaGit. Raporty sesji opisują błędy i ich poprawki.

## Wydanie i blokady

Produkcja **BLOCKED**: bieżąca integralność/konta SQL004/17, RPO≤60min,
trwały magazyn i klucz, rollback Render i handoff starych workerów. ZgodaA aktualna,
nie rozszerzona na006. Nie powtarzano SSH; TCP puste. Brak nowych kosztów.
Nowe FOCUS_CALENDAR_SCHEMA_ENABLED i FOCUS_CALENDAR_ENABLED domyślniefalse.
Opcjonalny profil006 z004, bez Google005. Wymaga osobnej zgody na migrację/deploy;
oba profile naraz mająSTOP. Zero produkcyjnych zmian/eksportów/restore/Meta/DM.
Nie zmieniono Focus1.0/2.0. Google nie jest warunkiem nowej funkcji ani celem następnej sesji.

## Pozostałe zadania i szacunek

Nie ma webpush, drag&drop ani testu nowego panelu na fizycznym iPhonie. Otwarta polityka
retencji metadanych, testy skali/paginacji i twardsze próby restartu natywnego procesu.
Raport tasków limit1000, reminders batch500; większa skala wymaga dodatkowych prac.
Szacunek nadal co najmniej5 sesji podstawowych +≥1DM; nie zmniejszony bez zamknięcia bramek.
Najważniejszy dalszy etap: walidacja retencji/skali i restartu, następnie zatwierdzony
plan wydania z funkcjamiOFF. Brak deklaracji gotowości produkcyjnej na podstawie mocków.
