# Autonomiczna praca Focus 3.0

Właściciel zatwierdził rutynowe kodowanie, testy, poprawki, review, merge i kontrolowane
wdrożenia w istniejącym zakresie/budżecie. Kolejne kroki nie wymagają nowego polecenia.
Wykonawcą koordynacji jest istniejący godzinowy automat, planer 08:30 przygotowuje
kolejkę. Nie dodajemy zegara, workera ani usług. Nie obiecujemy pracy między przebiegami.

## Źródła i wykonywalna kolejka

`scripts/codex_automation/operations_queue.json` zawiera priorytety, zakres, zależności
i kryteria odbioru. Jest kolejką operacyjną, nie zgodą `/codex approve`, konfiguracją
budżetu ani zamiennikiem admission. Obejmuje aktualny blokowany tor wykonawcy i
niezależną pracę bez modelu. Numer istniejącego Issue/PR nie oznacza nowego testu/replay.
Przed kolejnym pakietem zaktualizuj kolejkę na podstawie świeżych #39/Issues/PR;
DONE wymaga weryfikacji wyniku i dowodu, samo zamknięcie issue nie wystarcza.

Koordynator zbiera snapshot przez dostępne konektory GitHub/Render (bez sekretów):

```json
{
  "repository": "artgawlik-ui/ai-focus-3-0",
  "main_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "observed_at": "2026-11-17T18:00:00Z",
  "inventory_complete": true,
  "active_executor_runs": [],
  "leases": [],
  "task_states": {
    "technical-access": {
      "status": "READY", "verified": true,
      "evidence": ["konkretny dowód z GitHub/Render"], "attempts": 0
    }
  }
}
```

Przykład jest syntetyczny. `inventory_complete=true` ustawiaj dopiero po sprawdzeniu
wszystkich stron aktywnych workflow (w tym queued/waiting/pending), otwartych PR,
wdrożeń/instancji i aktualnych lease w #39. Przy niepełnym odczycie ustaw false.
`active_executor_runs` zawiera wykonawcę i konkurencyjne pakiety, nie same bezpłatne CI.
`leases` to aktywne zajęcia zakresu z `expires_at` w UTC; konflikty blokują wykonanie.
Stan brakujący/niezweryfikowany jest BLOCKED. Snapshot starszy niż 10 minut wymaga odczytu.

```bash
python scripts/codex_automation/operations.py --snapshot /tmp/focus-operations.json
```

Planner jest bez skutków ubocznych. Zawsze zwraca `paid_authorized=false`. READY oznacza
tylko zweryfikowany zakres offline, nie uprawnienie do API, bazy, merge lub wdrożenia.
Przed każdą mutacją odczytaj ponownie exact SHA, zajmij pakiet w #39 i zastosuj istniejącą
kontrolę expected SHA oraz wszystkie bramki. Maksimum dwóch prób dotyczy pracy offline
w pakiecie; błąd wymaga diagnozy przed ponowieniem. Zmieniony zakres dostaje nowy pakiet.
`uncertain_execution=true` zabrania automatycznego replay także po wygaśnięciu lease.

## Review i wydanie

Sprawdź diff i rzeczywiście zmienione zachowanie. `ci_state(checks, sha)` odrzuca zielone
wyniki innego SHA, wymaga obu workflow oraz uwzględnia ostatnią próbę. To pomoc przy
ocenie CI, nie kompletny GO produkcji. Nie scalać przy niezaliczonym audycie zależności.
Jeżeli GitHub wymaga dodatkowych kontroli, również muszą przejść. Rutynowy merge wykonuje
koordynator po review/CI i ponownej kontroli głowy PR. Dla produkcji wymagane są realne
dowody #10–13 (backup, rollback, dostęp i decyzja wydania). Nie usuwać required owner review.
Po merge sprawdź autoDeploy i aktualne wdrożenie przed triggerem. Potwierdź exact live SHA
i health; w razie niepewności zapisz BLOCKED, nie ponawiaj wdrożenia w ciemno.

## Dostęp i przerwy dostawcy

Istniejący worker używa credential w zabezpieczonym środowisku Render i wychodzącego
HTTPS GitHub; przeglądarka właściciela nie jest transportem. Dowód działającego pollingu
nie potwierdza wszystkich zakresów/ważności credential. Koordynator weryfikuje oddzielnie
każdą wymaganą operację i wygaśnięcie/odnowienie, bez publikacji tokenu/DSN. Brak narzędzia
administracyjnego lub owner review jest konkretnym blockerem, nie podstawą do szerszych
uprawnień, kopiowania osobistych tokenów lub otwierania prywatnej bazy.

Costs429: zachowaj rzeczywisty Retry-After i istniejący trwały termin; nie resetuj procesu
dla sondowania. Brak dowodu deadline nie uprawnia do skrócenia przerwy. Nie ponawiaj
#48/#50/#56/#58/#65; przy niepewnym stanie najpierw odczyt prywatnego trwałego snapshotu.
Model pozostaje OFF do rzeczywistych kosztów, właściwego transportu, taryfy/modelu,
binding/limitów, okna 09–18 Warszawa i wymaganych akceptacji. Limit8USD/2USD i zgoda50PLN
pozostają; żadnych nowych płatnych usług.

## Wznowienie i istotne raporty

Po każdym pakiecie zapisz w #39: task, owner, UTC expires_at, wejściowy/końcowy SHA,
PR/run, wyniki/dowody, liczba prób, stan, blocker i dokładny następny warunek. Zwolnij
lease po końcowym checkpointcie. Następny przebieg odtwarza te dane i rzeczywisty stan
GitHub/Render, bez zależności od poprzedniego procesu/scratch. W obrębie dostępnego
przebiegu kontynuuj następny gotowy zakres, a przy blokadzie wybierz niezależny offline.

`checkpoint(result, previous_fingerprint)` zwraca stały odcisk stanu; zapisz go w #39
jako `FOCUS_OPERATIONS_CHECKPOINT` wraz z bezpiecznym JSON. Kolejny przebieg podaje go
przez `--previous-fingerprint`. Zmiana samego czasu snapshotu nie powiadamia. Nowy wynik,
blocker, wymagane działanie lub następny zakres powiadamia. Nie dołączaj surowych payloadów
lub sekretów. Publikacja odbywa się tylko pod jednym aktywnym lease; odcisk nie jest
rozproszoną blokadą ani dowodem wysłania powiadomienia. Brak zmiany = bez nowego komentarza
i bez kolejnego raportu użytkownikowi.

## Status odbioru

Testy syntetyczne kolejki nie dowodzą produkcyjnego round trip ani płatnego wykonania.
Pełny odbiór autonomii wymaga dwóch rzeczywistych kolejnych ukończonych zadań z dowodami
review/CI/wyniku. Włączenie koordynatora i dodanie tego narzędzia nie kończy odbioru modelu.
