# CRM-24A — audyt formularza salonu i zależności PR #3

Data odczytu: 2026-11-16. Powiązania: #24, #28, #29–#31, PR #3 i #26.

## Zakres i dowody

Porównano źródła main `038b69aca0295b685c8d25ab44fbeb871247950a` oraz Draft PR #3 `e37ce5d1ce807b47af18e3354c3232296b8b26c6`. To audyt kodu, nie odbiór produkcji ani test danych klientów.

- `backend/schemas.py`: fragmenty SalonIn, SalonUpdate i ActivityIn są identyczne.
- `frontend/src/main.tsx`: fragment formularza salonu od listy pól do jego zamknięcia jest identyczny.
- `backend/db.py`: cały blob jest identyczny: `0cc311b6a515ecfc2aad5549681e48e296e64520`.
- `backend/main.py`: funkcje klucza dopasowania oraz tworzenia, edycji i przypisania salonu mają tę samą badaną logikę.
- Pełne pliki UI, schematów i backendu różnią się poza badanym zakresem. Nie oznacza to równości całego main i PR #3 (273 zmienione pliki według odczytu PR).

Źródła:
- [main — schematy](https://github.com/artgawlik-ui/ai-focus-3-0/blob/038b69aca0295b685c8d25ab44fbeb871247950a/backend/schemas.py)
- [PR #3 — schematy](https://github.com/artgawlik-ui/ai-focus-3-0/blob/e37ce5d1ce807b47af18e3354c3232296b8b26c6/backend/schemas.py)
- [main — formularz](https://github.com/artgawlik-ui/ai-focus-3-0/blob/038b69aca0295b685c8d25ab44fbeb871247950a/frontend/src/main.tsx)
- [PR #3 — formularz](https://github.com/artgawlik-ui/ai-focus-3-0/blob/e37ce5d1ce807b47af18e3354c3232296b8b26c6/frontend/src/main.tsx)

## Istniejące pola — nie implementować ponownie

| Wymaganie | Istniejące zachowanie w obu źródłach | Pozostała praca |
| --- | --- | --- |
| Nazwa | Pole wymagane w UI; backend 2–160 znaków | Spójne komunikaty i ograniczenia UI, bez nowego formularza |
| Miasto | Pole wymagane w UI; backend 2–100 znaków | Jak wyżej |
| Adres | Pole istnieje; backend maks.250; opcjonalne | Kontrakt dopasowania adresowego |
| Profil Instagram | Pole istnieje; backend maks.100; opcjonalne | Integracja normalizatora i testy kandydatów duplikatów |
| Źródło | source_url istnieje; typ url w UI; backend wymaga prefiksu HTTPS | Prefiks nie jest pełnym sprawdzeniem struktury URL |
| Opiekun | Tworzenie przypisuje bieżącego użytkownika; menedżer może potem zmienić opiekuna w szczegółach | Ocenić potrzebę wyboru przy tworzeniu; nie usuwać istniejącego bezpiecznego przepływu |
| Segment | Priorytety A+, A, B, C są dostępne | Nie usuwać C bez decyzji produktowej |
| Historia | Tworzenie/edycja/przypisanie zapisują Activity z autorem i datą | Osobny kontrakt kanału i potwierdzonego statusu kontaktu |
| Konflikt edycji | Update używa version i warunkowego SQL; konflikt daje409 | Zachować i rozszerzać tylko dla nowych ścieżek |

## Deduplikacja: czego obecny kod nie gwarantuje

`dedup_key` pochodzi z nazwy i miasta, a kolumna ma globalną unikalność. Adres i Instagram nie uczestniczą w tym kluczu. Poniższe wnioski wynikają ze źródeł; nie uruchamiano tych scenariuszy na produkcji:

1. Dwie placówki o tej samej nazwie i mieście, lecz innych adresach, mogą otrzymać ten sam klucz i zostać odrzucone. To nie spełnia docelowego rozróżnienia placówek z #24.
2. Ten sam profil Instagram przy zmienionej nazwie/miastach nie jest chroniony unikalnością znormalizowanego profilu.
3. Sama kontrola kandydata w aplikacji nie zabezpiecza równoczesnych insertów. Potrzebny jest przemyślany kontrakt DB, migracja i audyt kolizji na kopii; nie zmieniać istniejących kluczy lub rekordów na ślepo.
4. PR #26 dostarcza funkcję przygotowawczą, nie wdraża powyższych gwarancji do endpointu. Jego poprawiony head `157460700fb4ea7c711e629dc9821d68e7496ef8` odrzuca znaki kontrolne, aliasy Unicode→ASCII, niejednoznaczne ścieżki i userinfo. Został scalony jako `d0054de362550eb97b558d5e1ff6d2f1a5cf6041`.
5. Dopasowanie profilu nie oznacza zgody na kontakt, weryfikacji właściciela lub Meta recipient ID.

## Historia, role i brak wysyłek

ActivityIn obsługuje note, call, visit, email_received, follow_up. Nie ma w nim pełnego kontraktu draft/manual_sent/api_confirmed_sent/received/not_sent z #24. Nie utożsamiać notatki ani zadania agenta z potwierdzoną wysyłką. W modelu i badanych źródłach PR #3 nie znaleziono zamiennika tego kontraktu. To zakres #30/#31; pozostałych, odrębnych modułów nie wolno traktować jako dowodu spełnienia wymagań bez osobnego audytu.

Tworzenie działa jako zalogowany użytkownik; odczyt i edycja korzystają z istniejącego owner scope. Przypisanie wymaga roli menedżera i aktywnego odbiorcy. Nowy mechanizm dopasowania musi zachować ten zakres danych i nie ujawniać handlowcowi szczegółów cudzych klientów. Opt-out i konflikty pozostają osobnym etapem #31.

## Weryfikacja i kolejność

- Bezpośrednie porównanie odczytanych fragmentów schematów i formularza: równe. Model salonu: identyczny blob.
- PR #26:7 celowanych testów PASS; nowe przypadki odtwarzały12 błędnych dopasowań przed poprawką. Pełne Verify43917760421 i policy43917759307 PASS:203 testy,199 podtestów, Chromium/WebKit i audyty.
- Istniejące tests/test_api.py zawierają testy ról/własności, duplikatów i optimistic lock, importu, historii/no-send i opt-out. To pokrycie bazowe, nie dowód rozbudowanej deduplikacji po Instagramie/adresie.
- W tym docs-only audycie nie dodano testów lustrzanych ani fikcyjnego PASS dla brakujących funkcji. Testy nowych zachowań powstaną razem z minimalną implementacją odpowiedniego kontraktu.

Następne: #29 — doprecyzować walidację i zachowanie formularza, wykorzystując istniejący UI. Potem #30 — historia z dowodami statusu; #31 — opt-out, role i współbieżność. Każde jako mały niezależnie sprawdzony pakiet. Nie kopiować zbiorczo PR #3, nie zmieniać produkcyjnej bazy, nie wysyłać DM i nie traktować tego raportu jako GO dla produkcji.
