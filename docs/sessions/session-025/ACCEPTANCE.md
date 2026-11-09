# Sesja025 — zabezpieczenie bootstrapu, kryteria przed zmianą

Wejście: pełny workflow024180d776/42653906423 SUCCESS/364 PASS.

1. Pozostały VERIFICATION_PASSWORD nie tworzy żadnego technicznego managera,
   również przy pierwszym uruchomieniu i ponownym starcie. Bez nowej flagi aktywacji.
2. Istniejące konta (w tym wyłączone techniczne) i sesje/hash haseł pozostają bez zmian.
3. Istniejąca baza nie wymaga utrzymywania hasła inicjalizującego do ponownego startu.
4. Pusta syntetyczna baza: dokładnie1 początkowy manager z hashem Argon2, błędne/missing
   wymagane ustawienia odrzucane bez utworzenia kont. Powtórzenie nie zmienia danych.
5. Brak haseł, hashów, tożsamości kont i sekretów w stdout/wyjątkach/raportach.
6. Testy wyłącznie syntetyczne. Pełny końcowy CI i aktualizacja macierzy gotowości,
   raportu/RESUME/raportu porannego. PR3Draft. Brak produkcji, kont/sekretów, konfiguracji,
   merge/deploy/migracji/export/restore/PITR/Google/Meta/DM i kosztów. Focus1/2 nietknięte.

Nie jest to dezaktywacja istniejącego konta produkcyjnego ani unieważnienie sesji.
Bieżący stan kont nadal wymaga zatwierdzonego odczytu A i prywatnej tożsamości.
