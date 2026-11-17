# Kontrakt paginacji i bezpieczeństwo

Nowe GET /api/focus-calendar/{contacts,tasks,visits,notifications}/page:
items,total,limit,offset,has_more. Limit1–100,offset0–100000, domyślnie20. Stabilny
końcowy klucz ID (powiadomienia: key), więc remisy czasu/nazwy nie powielają rekordów
w niezmiennym zbiorze. Lista jest aktualna, bez izolowanego snapshotu między żądaniami:
równoległa zmiana sortowanego pola może przesunąć rekord — odświeżyć pierwszą stronę.
Nie przedstawiamy offset jako gwarancji spójnego eksportu.

Filtry: search (literalne podciągi salonu/handlowca i tytułu task), representative_id,
priority; tasks dodatkowo status/from_date/to_date, contacts day/due_only/from_date/
to_date, visits day/days/status. Wszelkie wartości są parametrami wiązanymi, nieSQL.
Daty biznesowe Europe/Warsaw; dane kontaktu normalizowane do timestamptz, przyszłe
lub nieprawidłowe dowody ignorowane. Ścisłe scope aktualnego opiekuna wSQL; manager
może wybrać handlowca, handlowiec dostaje403 dla innego ID. Opt-out nie jest kontaktem.

Stare listy zachowują JSONarray i przyjmują limit/offset (domyślnie100), z nagłówkami
X-Focus-Total i X-Focus-Has-More. Stare /api/appointments również ograniczone100 i ma
stabilnyID; plan tras filtruje confirmed przed tym limitem. PWA korzysta z nowych
stron, selektory klientów również wyszukują stronicowo zamiast ładować całyCRM.
Raporty zwracają podgląd20 rekordów + pełne counts/pages i agregaty zespołu. Dodatkowe
filtry list nie zmieniają pełnego podsumowania dnia/handlowca; jest to opisane wUI.

Powiadomienia: kwalifikacja aktualnego terminu/statusu/opiekuna przed LIMIT. Partie
maksymalnie500task+500visit wykluczają już istniejące bieżące klucze. ONCONFLICT nie
zmienia odczytu/dat tego samego właściciela. Zmiana opiekuna odświeża prywatną skrzynkę.
Źródło feed wyliczane raz (MATERIALIZED), z filtrem właściciela przed materializacją;
nieprzeczytane stare dane nie wypierają nowych przez arbitralny rawLIMIT100.
Zero minut dla wizyty to osobny terminowy komunikat z24hoknem nadrobienia, nie fikcyjny
push. Opóźnienie workerów dłuższe niż okno wymaga diagnostyki — nie gwarantujemy deliverySLA.

Worker planowania tworzy do100 follow-up/user/przebieg, wyklucza zakończone/bieżące
cykle wSQL i ponownie sprawdza kontakt/opt-out pod wspólną blokadą. Dla dużego pierwszego
uruchomienia to kontrolowana kolejka, nie obietnica natychmiastowych10tys zapisów.
Dotychczasowy globalny advisorylock workera i naturalne klucze pozostają.

Opcjonalne indeksy007 w profilu native, down006 usuwa wyłącznie te indeksy; tabele,
klienci i historia pozostają. Domyślny profil004 nie zmienia się. Nie wykonywać migracji
na produkcji bez zgody, kopii/restore, RPO i nowego manifestu21tabel. ZgodaA nadal004/17.
EXPLAIN dla szerokich list może prawidłowo wybierać SeqScan/HashJoin zamiast indeksu;
nie przypisujemy wzrostu wydajności samemu dodaniu indeksów. Są one dodatkowym kosztem
zapisu/miejsca i wymagają oceny na rzeczywistym rozkładzie danych przed wdrożeniem.
