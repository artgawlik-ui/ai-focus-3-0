# Historia kontaktów: wiarygodne statusy wiadomości

Pierwsza bezpośrednia poprawka Issue #30, bez płatnego wykonawcy.
Baza: main `1bac028551f738c50dee285b8125342cccf566fc`.
Sprawdzono też Draft PR #3 (`e37ce5d`) i PR #17 (`d8894b82`).
Pozostają odrębnymi, niescalonymi propozycjami; tej poprawki nie wprowadzono
do ich gałęzi ani nie skopiowano ich procesu sprzedażowego do main.

## Problem i wynik

Podpisany syntetyczny webhook z `is_deleted: "false"` zmieniał otrzymaną
wiadomość na `deleted` i usuwał jej treść. Przyczyną była interpretacja
niepustego tekstu jako wartości prawdziwej. Ponadto `is_echo: true` ze
sprzecznym nadawcą był traktowany jako nowa odpowiedź klienta.
Oba wzorce występują również w sprawdzonych gałęziach PR #3/#17.

Wspólna walidacja dopuszcza tylko wartości logiczne dla obecnych flag
`is_echo`/`is_deleted` i wymaga własnego konta jako nadawcy echo.
Wykonuje się przed zapisem/deduplikacją oraz ponownie przed przetworzeniem
historii, obejmując także wcześniej zapisane zdarzenia kolejki.
Odrzucone zdarzenie nie zajmuje klucza poprawnego późniejszego potwierdzenia.

## Znaczenie istniejących stanów

| Stan | Źródło i znaczenie |
|---|---|
| `draft` | Lokalny szkic; nie wysłano wiadomości. |
| `approved` | Zatwierdzony szkic; nie jest dowodem wysyłki. |
| `manual_sent` | Oświadczenie uprawnionego operatora, bez potwierdzenia API. |
| `api_confirmed_sent` | Podpisane echo dostawcy dla własnego konta; nie oznacza przeczytania ani potwierdzenia dostarczenia. |
| `received` | Prawidłowe zdarzenie przychodzące. |
| `deleted` | Zdarzenie usunięcia z flagą logiczną `true`; treść jest czyszczona. |
| `not_sent` | Osobny stan ręcznego procesu w Draft PR #17; nie dodano go do main w tej zmianie. |

## Sprawdzenia

Test regresji odtworzył przed poprawką zmianę `received` → `deleted` dla
tekstowego `"false"`. Nowe scenariusze obejmują nieprawidłowe typy obu flag,
odczyt historii i treści, brak fikcyjnej odpowiedzi/aktywności CRM,
stare zdarzenia kolejki, brak zatrucia deduplikacji oraz poprawne stany
otrzymania, echo i usunięcia. Istniejący test ręcznego wysłania zachowuje
rozróżnienie `manual_sent` i potwierdzenia API.

Wyłącznie syntetyczne webhooki z testowym podpisem i izolowana baza testowa.
Bez rzeczywistych kont, wiadomości, sieci Meta, zmian migracji lub flag,
merge/deploy, produkcyjnych danych i zmian automatyzacji Codexa.
Gotowość produkcyjna i rzeczywista integracja pozostają osobnymi etapami.
