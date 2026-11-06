# Raport postępu — 2026-11-06, Europe/Warsaw

Sesja016 zamknięta nową decyzją właściciela: zaprzestanie rozwoju Google. Sesja017:
natywny kalendarz i monitoring CRM za FOCUS_CALENDAR_ENABLED=false.
Dodano listę ponownego kontaktu, progi i indywidualną częstotliwość, zadania z wynikiem,
cykle, deduplikację, przypomnienia wewnętrzne i raport menedżera. Nie utożsamiamy zadania,
szkicu ani zaplanowanej wizyty z kontaktem. Szczegóły: docs/sessions/session-017/REPORT.md.
Nowe25 przypadków:24 native +1 lifecycle. Końcowa lokalna regresja55/55PASS (30.15s), build/compile/sh/diffPASS;
wynik pełnego CI wymagany osobno (nie przepisywać wyniku wejścia259).
Commity: git log --oneline -- docs/sessions/session-017/REPORT.md; PR3 Draft:
https://github.com/artgawlik-ui/ai-focus-3-0/pull/3. Sesja017 ad348f0 CI42302108082 SUCCESS:284PASS, Chromium/WebKit i audyty0 podatności.
Google/Meta/DM/push nieaktywne; zero produkcyjnych operacji i kosztów, Focus1/2 nietknięte.
Blokady: bieżący SQL004/integralność, RPO60, magazyn/klucz, rollback/handoff; zgodaA aktualna.
Nowy opcjonalny profil006 wymaga osobnej zgody; nie rozszerza A. Szacunek≥5 sesji +≥1DM.
Następny dzień: ergonomia terminu Warszawa, pełny raport dnia i dalsza walidacja workerów.
Nie deklarujemy pracy w tle po zakończeniu bieżącego wykonania.

Sesja018: osobny schema/runtime switch, datetime-local Warszawa z walidacją DST,
odczyt własnych ustawień, pojedynczy aktualny próg przypomnienia i blokada rekordu
salonu przeciw równoległej zmianie opt-out. Nowych9 testów (łącznie34 nowych od015).
Lokalnie48PASS/21.00s; pełne CI nowego SHA wymagane przed PASS.
Raport: docs/sessions/session-018/REPORT.md. Aktualny etap018, następny raport dnia.
