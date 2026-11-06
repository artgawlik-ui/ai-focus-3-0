# Sesja018 — walidacja terminów, przełączników i przypomnień

Wejście ad348f0, pełne CI42302108082 SUCCESS/284PASS potwierdzone logiem. Kod017
zachowany; produkcja i Google pozostają niezmienione. Nowych9 testów.

## Ukończone

- FOCUS_CALENDAR_SCHEMA_ENABLED wybiera profil006 niezależnie od runtime
  FOCUS_CALENDAR_ENABLED. Obie flagi domyślnie false; runtime wymaga obu. Można wyłączyć
  funkcję bez utraty możliwości startu aplikacji po006. Start używa tego samego parsera.
  Nie obowiązuje już historyczne wiązanie flagi funkcji i profilu z raportu017.
- Formularze tasków mają datetime-local w Europe/Warsaw, bez ręcznego wpisywania ISO.
  Wiosenna luka DST ->422; jesienna dwuznaczność wymaga jawnego fold0/1. Serwer odrzuca
  brak/oba terminy przy tworzeniu; dotychczasowy ISO API pozostaje zgodny.
- Ustawienia okresów i przypomnień są odczytywane z bazy, a nie pokazywane stale jako
  domyślne po ponownym otwarciu panelu. Uprawnienia do zmiany bez rozszerzenia.
- Przypomnienie wizyty tworzy najbliższy pasujący próg, nie trzy identyczne naraz;
  aktywne centrum filtruje wcześniejsze progi, zmieniony termin i wizyty już rozpoczęte.
- Operacje zapisu zadania blokują również rekord salonu (FOR NO KEY UPDATE), więc
  równoległy PUT opt-out jest serializowany i status czytany ponownie po oczekiwaniu.

## Dowody

Lokalny syntetyczny PG17, bez danych produkcyjnych. Komenda pytest -q
 tests/test_native_planning.py tests/test_worker_lifecycle.py: **48passed,0failed,0skipped,
 21.00s**. Zawiera33 natywne i15 lifecycle, nie sumować z017. Dziewięć nowych przypadków:
5 wariantów DST, niezależne flagi, odczyt ustawień, pojedyncze/aktualne przypomnienie,
bariera wątku podczas niezatwierdzonej transakcji opt-out ->409 po commicie.
Build/compileall/sh-n/diff-check PASS. Dwa ostrzeżenia deprecacji narzędzi zewnętrznych,
jak w017; bez wyciszenia. E2E używa nowego datetime-local, oba silniki wymagają zielonego
CI końcowego SHA; dowód w ChecksPR3/raporcie porannym. Nie jest to test fizycznego iPhone.

## Rollout i ograniczenia

Po osobno zatwierdzonej migracji006 schema=true, runtime=false. Najpierw kontrola21tabel,
liczności/fingerprintów, kont i procedury odzyskiwania, dopiero osobna zgoda na runtime.
Nie zmieniono zakresu zgodyA (tylko004/17) ani istniejącego schematu/rekordów produkcji.
Wyłączenie runtime zatrzymuje native tick i blokuje API; schema pozostaje true. Cofnięcie
markera006->004 zachowuje dane, wymaga osobnej zgody; nie łączyć profili005/006 bez planu.
Nie uruchomiono żadnej z tych czynności na produkcji.

Brak push, drag&drop, pełnego raportu odbytych wizyt i pomiaru pracy na fizycznym iPhonie.
Retencja metadanych nadal wymaga polityki. RPO60, aktualne SQL, magazyn/klucz,
rollback/handoff pozostają BLOCKED. Brak Google/Meta/DM/produkcji i nowych kosztów.
Szacunek co najmniej5 podstawowych +≥1DM bez redukcji. Następny bezpieczny etap:
pełny raport dnia/zbliżających się wizyt i zaległości, przy zachowaniu rozdziału planu
od rzeczywiście zarejestrowanych działań. Kod PASS dopiero po końcowym CI.

Potwierdzone CI:8c64fa0ec9189aa95d8e14929f0106f6ede1e649,
https://github.com/artgawlik-ui/ai-focus-3-0/actions/runs/42303042647 SUCCESS,
293testyPASS, Chromium/WebKit/build/audytyPASS,0 znanych podatności. Kod018 PASS.
Kontynuacja019; produkcyjne wydanie pozostaje BLOCKED.
