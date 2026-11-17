# Sesja 002 — kryteria przed implementacją

1. HEAD bazowy a9e2fab i obie kontrole push/PR tego SHA potwierdzone przez GitHub; PR Draft, brak merge.
2. Nowy preflight nie importuje aplikacji, nie wykonuje DML/migracji/backupów, używa REPEATABLE READ READ ONLY, krótkich timeoutów i kończy ROLLBACK.
3. Domyślnie wyłącznie localhost i baza focus3_test; kanał wewnętrzny wymaga jawnego osobnego dopuszczenia. W tej sesji nie wykonujemy połączeń z Render ani produkcją.
4. Syntetyczne testy: zgodność zakresu, rozbieżne liczby/ID/hash/schema/revision/zależności -> BLOCKED; wyjście nie ujawnia rekordów, poświadczeń ani identyfikatorów.
5. Instrukcja Meta rozdziela kod od konfiguracji panelu i Development od produkcji; aktualne oficjalne źródła albo jawna blokada ich weryfikacji; bez prawdziwego OAuth/Graph/DM.
6. Release checklist: 004, brak nowej migracji, świeży szyfrowany backup+sprawdzony undo, rollback, Meta OFF, konto techniczne, smoke i count/SHA po deployu. Niewykonane operacje produkcyjne pozostają BLOCKED.
7. Raport z komendami/wynikami, plikami, commitami, ograniczeniami i licznikiem 5 podstawowych + ≥1 DM. Nie zmniejszać licznika za przygotowanie bez zamknięcia kryteriów operacyjnych.
