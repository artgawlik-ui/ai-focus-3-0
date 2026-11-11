# Pilota Codex: `gpt-6-luna`

Ten dokument opisuje kontrolowany przepływ zadania dokumentacyjnego w Ai Focus 3.0.4. Samo utworzenie Issue nie uruchamia modelu. Rzeczywisty pilot wymaga osobnej autoryzacji zadania i zatwierdzenia chronionego środowiska `codex-development`.

## Przepływ Issue → Codex → Draft PR

1. Zleceniodawca tworzy małe Issue z celem, dozwolonymi ścieżkami, kryteriami akceptacji i komendami testów. Treść nie może zawierać danych klientów, danych z Instagrama ani sekretów.
2. Uprawniona osoba zatwierdza dokładną treść Issue zgodnie z procedurą repozytorium. Zmiana treści wymaga ponownego zatwierdzenia. Sama etykieta ani nieautoryzowany komentarz nie są zgodą.
3. Workflow sprawdza zgodę, stan Issue, repozytorium, limity zmian i ochronę środowiska. Po przejściu bramek uruchamia `gpt-6-luna` na jednorazowym runnerze i izolowanej gałęzi.
4. Propozycja modelu jest niezaufana. Zaufany kontroler sprawdza ograniczenia plików i publikuje ją jako osobny Draft PR. Draft wymaga przeglądu człowieka.
5. Walidacja syntetyczna przypięta do dokładnego SHA kandydata raportuje status kontroli w GitHub Actions. Wynik, SHA i powiązany Draft PR są dowodem wykonania; samo Issue ani utworzenie Draft PR nie oznaczają zaliczenia testu.

## Zabezpieczenia automatyzacji

- Uruchomienie wymaga jawnej zgody na konkretne Issue, zatwierdzenia środowiska `codex-development` i włączonych bramek kosztowych. Błąd lub brak uprawnień zatrzymuje proces.
- Wykonawca ma tylko odczyt repozytorium, ograniczone uprawnienia, sandbox workspace i jednorazowy runner. Sekret dostawcy, jeśli osobno autoryzowany, jest dostępny wyłącznie wykonawcy; nie przekazuje się sekretów produkcyjnych.
- Kontroler ogranicza zmieniane ścieżki do `backend/`, `frontend/src/`, `tests/` i `docs/`, sprawdza rozmiar oraz wzorce sekretów. Workflow, instrukcje, zależności, migracje i pliki operacyjne są poza zakresem pilota.
- Publikacja używa zwykłego push bez force i tworzy Draft PR. Walidacja ma tylko niezbędny odczyt; raport zawiera status i odnośniki, nie swobodny tekst modelu ani sekretne dane.
- Nie wykonuje się merge, wdrożenia, migracji, połączeń do produkcyjnych usług ani operacji na koncie Instagram. W razie błędu nie ponawia się automatycznie płatnego uruchomienia.

## Testy lokalne

W środowisku deweloperskim uruchom syntetyczne testy polityk automatyzacji:

```sh
python -m unittest discover -s tests/automation -v
```

Testy te używają fixture'ów i nie wywołują Codexa ani zewnętrznych usług. Pełny zestaw projektu uruchamiaj wyłącznie w odizolowanym środowisku z testową bazą syntetycznych danych, nigdy z konfiguracją klienta lub produkcji. W CI pełna walidacja obejmuje testy backendu, build frontendu, testy przeglądarkowe i audyty zależności; wynik raportuje się dla SHA kandydata w GitHub Actions. Ten raport CI nie jest częścią lokalnego testu.

## Status tego opisu

Dokumentacja nie aktywuje workflow ani środowiska. Bez osobnej autoryzacji i zatwierdzenia `codex-development` nie uruchamia się modelu, nie tworzy Draft PR i nie generuje raportu GitHub Actions. Lokalny wynik testów syntetycznych nie zastępuje tych dowodów.
