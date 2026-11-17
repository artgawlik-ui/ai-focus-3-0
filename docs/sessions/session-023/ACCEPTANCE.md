# Sesja 023 — kryteria przed implementacją

Wejście: sesja 022, a11c8aa, pełny workflow PR 42639643983 SUCCESS.

1. Panel menedżera pokazuje wyłącznie metadane kolejek, bez treści CRM i sekretów.
2. Nowa flaga FOCUS_DIAGNOSTICS_ENABLED domyślnie OFF; tylko literalne true włącza
   podgląd. Niczego nie uruchamia, nie zmienia istniejących flag ani zachowania workera.
3. Uprawnienia egzekwowane przez API: anonimowy 401, handlowiec 403, manager dozwolony.
4. Schemat native OFF: brak zapytań do opcjonalnych tabel. Runtime OFF nie aktywuje się
   przez odczyt. Brak schematu przy błędnej fladze daje kontrolowany brak diagnostyki.
5. Przypomnienia oczekujące liczone według tych samych źródeł i deduplikacji co worker;
   anulowanie, opt-out i nieaktywny opiekun wykluczają nieaktualne wpisy.
6. Heartbeat nie jest dowodem wykonania cyklu. Brak/stary/uszkodzony/pliki z przyszłości
   są pokazywane jako niepotwierdzony stan, bez PID i zawartości pliku.
7. Podgląd retencji w UI używa istniejącego endpointu; bez przycisku wykonania,
   bez DELETE, archiwizacji, aktywacji flag i bez migracji. Odczyty nie zmieniają danych.
8. Testy na syntetycznym PostgreSQL, E2E Chromium/WebKit, build i oba audyty PASS
   dla końcowego SHA przed oznaczeniem sesji PASS. PR #3 pozostaje Draft.

Produkcja nadal BLOCKED; zgoda A nie rozszerzona. Bez produkcji, migracji 007,
Google, Meta/DM, merge/deploy, eksportów/restore i kosztów. Focus 1.0/2.0 nietknięte.
