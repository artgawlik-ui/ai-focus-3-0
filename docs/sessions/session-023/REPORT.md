# RAPORT AI FOCUS 3.0.4 — SESJA 023

## Wejście i zakres

Sesja 022 zamknięta na podstawie pełnych workflow a11c8aa: PR 42639643983 i push
42639630411 SUCCESS. 335 testów, build, Chromium/WebKit oraz audyty PASS, 0 znanych
podatności. Potwierdzenie zapisano w 323a8a8, bez nadpisywania cudzych zmian.
Kryteria sesji 023 zapisano przed implementacją w ACCEPTANCE.md.

## Rzeczywista funkcja

Nowy panel „Kolejka i retencja Focus” w ustawieniach menedżera. Ręczny odczyt pokazuje
liczniki agenta, wiek najstarszego queued, zweryfikowany sygnał lokalnego procesu,
stan pauzy i aktualne przypomnienia jeszcze niezapisane przez generator. Bez treści
klientów, kont, wyników analizy, sekretów i PID. Heartbeat nie jest sukcesem cyklu;
UI wyraźnie podaje brak dowodu ostatniego natywnego przetwarzania.

Nowa flaga FOCUS_DIAGNOSTICS_ENABLED domyślnie OFF, fail-closed. Nie aktywuje żadnej
innej flagi. Schemat OFF pomija opcjonalne tabele; runtime OFF nie zabrania bezpiecznego
podglądu, ale nadal blokuje działania. Niedostępny schemat daje kontrolowany status.
Odczyty przypomnień używają źródeł generatora i identycznej deduplikacji. Nie dodano
nowej kolejki, procesu, migracji ani zależności.

Istniejący endpoint retencji udostępniono w panelu wyłącznie jako podgląd kandydatów.
Brak wykonawcy usuwania/archiwizacji i przycisku aktywacji. Dane CRM, kontakty i wizyty
nigdy nie są usuwane przez tę funkcję. Szczegóły: OPERATIONS_PREVIEW.md.

## Testy i dowody

- `pytest -q tests/test_native_diagnostics.py`: 24 PASS / 0 FAIL / 0 SKIP, 9.87 s.
- Regresja diagnostics + pagination + planning + lifecycle + capture: 109 PASS,
  69.04 s. Obejmuje 23 pierwsze nowe przypadki; późniejszy test nieprawidłowej daty
  kolejki jest objęty powyższym pełnym zestawem 24. Zestawów nie sumować.
- Testy: flagi, 401/403, brak danych osobowych/sekretów, świeży/stary/błędny/przyszły
  sygnał procesu, brak pliku, deduplikacja i opt-out, nieaktywny opiekun, runtime/schema
  OFF, brak tabel, nieprawidłowa data, brak DML oraz zgodność fingerprintów przed/po.
- `npm run build --prefix frontend`: PASS, TS i Vite (269.63 kB JS przed gzip).
- `python -m tests.ci_e2e`: lokalnie Chromium i WebKit PASS; test panelu i retencji,
  CRM/agent/wizyty/paginacja/offline/logout zachowane. Emulacja, nie fizyczny iPhone.
- Przy jednej lokalnej próbie WebKit nie otworzył dialogu wizyty po wpisaniu daty.
  Test teraz kończy edycję daty klawiszem Tab i weryfikuje jej wartość przed kliknięciem;
  pełny scenariusz ponownie przeszedł. Bez zwiększania timeoutów i pomijania kroków.
- Pełny końcowy CI tego kodu musi potwierdzić 359 testów, oba silniki, build i audyty.
  Do tego momentu sesja 023 IN PROGRESS, nie PASS. Wynik nie jest dziedziczony z 022.

## Bezpieczeństwo, ograniczenia i wznowienie

Nie zmieniono produkcji, Render, danych klientów, sieci, sekretów, kosztów ani uprawnień.
Bez merge/deploy, migracji 007, export/restore/PITR, Google/Meta/DM. Focus 1.0/2.0
nietknięte. PR #3 pozostaje Draft. Prywatne ZIP-y zachowane poza Git.

Wydanie produkcyjne BLOCKED: aktualny SQL004/17 i konta, RPO≤60 min, trwałość magazynu
kopii i klucza, rollback Render, zatwierdzony handoff workerów. Zgoda A nie rozszerzona.
Sygnał procesu jest lokalny, nie zbiorczy dla replik. Podgląd nie potwierdza recovery
ani pracy cyklu. Koszt agregacji rośnie z danymi; panel nie odpytuje automatycznie.

Szacunek nadal ≥5 sesji podstawowych + ≥1 DM. Nie zmniejszamy go za sam development.
Następny krok: zweryfikować końcowe CI dokładnego SHA, zapisać wynik w raporcie i
RESUME. Potem kontrole wydania wymagają wskazanych wcześniej dowodów i osobnych zgód.
