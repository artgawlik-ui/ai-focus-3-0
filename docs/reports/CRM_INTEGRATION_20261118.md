# Kandydat integracyjny CRM

Baza main: a2d118bb2c6924e6ae8eb8379750e46c904c345d, po scaleniu poprawki #71.
Źródło funkcji: Draft PR #17 d8894b82c4989f4743fb8c254f46b631f5a96a48,
zawierający Draft PR #3 e37ce5d1ce807b47af18e3354c3232296b8b26c6.

To oddzielna propozycja integracji kodu, bez scalenia #3/#17, migracji
produkcyjnych, wdrożenia, aktywacji Meta, Google lub płatnego wykonawcy.
Historyczne raporty ze źródłowych gałęzi nie są dowodami bieżącej produkcji.

## Rozwiązanie konfliktów

- RESUME.md zachowuje aktualny punkt wznowienia main; starsze dowody pozostają
  w historii PR #3/#17 i docs/sessions. Nowa notatka wyraźnie oznacza kandydata.
- tests/production_browser_check.py łączy izolowany adres, osłonę transportu,
  bezpieczne przechwytywanie obrazu i scenariusze CRM ze źródłowej gałęzi
  z helperem menu dotykowego, testem dwukrotnego otwarcia oraz kontrolowanymi
  powtórzeniami WebKit z main. Nie usunięto tych asercji na rzecz starszych kliknięć.
- Automatyczny merge frontend/src/main.tsx zachowuje setMobile(true),
  aria-expanded i aria-controls. backend/meta_inbox.py zachowuje walidację #71
  w obu ścieżkach oraz wcześniejsze zabezpieczenia PR #3.
- Aktualne esbuild i workflow automatyzacji main pozostają. Przeniesiony
  workflow Verify zachowuje dotychczasowe wyłączenie operatorskiego cleanup
  z Draft #3; nie jest to pełny test tego narzędzia.

## Odbiór

Wymagane są wyniki CI dla dokładnego SHA tego kandydata: testy PostgreSQL,
build, Chromium/WebKit, scenariusz dnia sprzedaży bez zewnętrznego transportu
i audyty zależności. Wynik #71 nie zastępuje tego odbioru.
Nawet zielone CI nie zamyka bramek produkcji opisanych w PRODUCTION_READINESS.
