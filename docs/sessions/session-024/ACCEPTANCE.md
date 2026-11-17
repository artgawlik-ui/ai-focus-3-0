# Sesja 024 — kryteria przed pracą

1. HEAD/PR/CI wejścia 80f4652 potwierdzone; PR #3 Draft, cudze pliki zachowane.
2. Tylko inspekcja istniejącego kanału A. Bez aktywnego zatwierdzonego kanału:
   0 SSH,0 SELECT produkcji, BLOCKED; bez alternatywnego publicznego konektora SQL.
   Dokładne cztery SELECT-y005 pozostają niezmienione (004/17 tabel i prywatne ID).
3. Aktualne odczyty metadanych provider/katalog dokumentacji: rozdzielić dostępność
   funkcji od dowodu RPO≤60 min, trwałość magazynu/klucza i możliwość odzyskania.
   Brak dowodu oznacza BLOCKED; bez eksportu, restore/PITR i konfiguracji.
4. Przećwiczyć na syntetycznym profilu native007: pauza, zatrzymanie w transakcji,
   przejęcie przez nowe procesy, brak częściowych/podwójnych przypomnień i szkiców,
   respektowanie opt-out. Wykorzystać istniejące testy, uzupełnić rzeczywistą lukę.
5. Sprawdzić odczyt starego API d15265b na schemacie z opcjonalnymi tabelami native,
   zachowanie fingerprintów wszystkich tabel. Nie uruchamiać starego workera przy
   rollbacku bez osobnej kontroli; stary kod nie zna nowej pauzy ani blokad.
6. PRODUCTION_READINESS: dla każdego gate PASS/BLOCKED, dowód, luka, ryzyko,
   następna bezpieczna czynność i wymagane zatwierdzenie. Gotowość kodu ≠ produkcji.
7. Testy regresji/bezpieczeństwa, build, oba silniki i audyty w pełnym CI dokładnego
   końcowego SHA; raport024, RESUME, raport poranny, push i Draft PR aktualne.

Zero produkcyjnych zmian, migracji, export/restore/PITR, merge/deploy, cleanup/DELETE,
sekretów/sieci/uprawnień/kosztów. Bez Google i aktywacji Meta/DM. Focus1/2 nietknięte.
