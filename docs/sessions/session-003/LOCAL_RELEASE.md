# Lokalny dry-run i checklisty recovery

## Wykonanie lokalne

```sh
python -m scripts.release_dry_run \
  --profile docs/sessions/session-003/synthetic-profile.json
```

Wynik `dry-run-result.json`: PASS_LOCAL oznacza tylko spójność dostarczonego profilu
syntetycznego. Boolowskie potwierdzenia w profilu są fixture, a nie dowodem bieżącej kopii,
konta lub deployu. Żadne pole nie udziela zgody na produkcję. Narzędzie nie łączy się z DB/siecią,
nie odczytuje sekretów/produkcyjnego env, nie zmienia flag i nie uruchamia komend wdrożenia.
Każdą flagę sprawdza osobno; true, pusty lub nieparsowalny wpis blokuje wydanie profilu.
Brak flag oznacza domyślne false zgodne z kodem przy legacy OFF. Dla rzeczywistej decyzji
należy ponownie ustalić efektywne ustawienia i dziedziczenie w zatwierdzonym kanale.

Test integracyjny lokalnie: health 3.0.4, odczyt syntetycznego salonu, prywatne API 401,
OAuth/subscription/webhook wyłączone, bezpośredni DM transport 403, owner login/logout,
deaktywacja konta technicznego i unieważnienie jego sesji. Zapisy wyłącznie na focus3_test.
Nie jest to smoke produkcji ani potwierdzenie aktualnej konfiguracji Render.

## Recovery — warunki przyszłego wydania

1. Właściciel zatwierdza źródło i miejsce trwałego przechowywania aktualnej kopii.
   Zapisać czas, sumę SHA, wersję dump/serwera i revision; kopię szyfrować, klucz oddzielnie.
2. Sprawdzić retencję całego cyklu: pliki, wersje obiektów, lifecycle, zasady usunięć,
   uprawnienia odczytu i sposób odtworzenia klucza. Kod scripts/offsite_backup.py wymaga
   potwierdzonej retencji bucket lifecycle 30 dni. Nie potwierdzono jej konfiguracji;
   nie włączano offsite ani nowego magazynu. Koszt/retencja wymagają osobnej decyzji.
3. Test restore na izolacji: count/SHA wszystkich 17 tabel, head 004, ograniczenia/indeksy,
   brak uruchomienia aplikacji/agentów i połączeń Meta, usunięcie jawnych plików po teście.
   Lokalny test szyfrowanej kopii i celowanego undo ma dowód w bazowym zielonym CI;
   nie zastępuje odtworzenia świeżej rzeczywistej kopii po zgodzie A.
4. Zatwierdzony celowany undo cleanup zachować zaszyfrowany, oddzielnie od raportu.
   Nie odczytywano historycznych plików, nie stwierdzamy ich trwałości.
5. Wyznaczyć RPO/RTO na podstawie rzeczywistych operacji; nie deklarować ich z lokalnego
   czasu pytest. PITR Render i dostępność wcześniejszego deployu nie są teraz sprawdzone.
6. Przed deployem zapisać rzeczywisty commit/deploy rollbacku zgodny z 004 i test kompatybilności.
   Bez nowej migracji nie wykonywać downgrade; zachować inbox, dane CRM, rejestr usunięć,
   opt-out i unieważnione sesje. Pełny restore produkcji jest inną, osobno zatwierdzaną operacją.

Po przyszłym deployu: health/HTTPS/wersja/commit, owner login, prywatne API bez sesji 401,
Meta efektywnie OFF, test offline PWA bez cache CRM. Count/SHA przed i po w uzgodnionym
oknie bez zapisów; każda różnica wyjaśniona, nie ignorowana. Zmiany sesji/jobów również
wymagają rozliczenia. Nie tworzyć testowych salonów w produkcji bez osobnego dopuszczenia.
