# Pomiary sesji022 — wyłącznie dane syntetyczne

PostgreSQL17, Docker1CPU/512MiB; PythonAPI/TestClient na hoście. To nie jest sprzęt
Render, obietnicaSLA ani test fizycznegoiPhone. Małe teksty syntetyczne; brak testu
bardzo dużych notatek i rzeczywistego ruchu wieloużytkownikowego. Jedno rozgrzanie,
potem5 odczytów (przed indeksami3). Tabela: mediany ms, strona20 rekordów.

| Salony | Kontakty | Zadania | Wizyty | Powiadomienia | Raport |
|---:|---:|---:|---:|---:|---:|
| 300 | 9.917 | 7.141 | 8.312 | 10.996 | 31.099 |
| 1000 | 14.208 | 7.430 | 9.621 | 31.750 | 50.067 |
| 5000 | 39.001 | 13.431 | 16.342 | 53.573 | 173.006 |
| 10000 | 80.369 | 23.597 | 27.254 | 101.467 | 320.594 |

Contacts/tasks/visits/report to odczyt managera całego zespołu. Powiadomienia mierzone
na koncie handlowca, który ma120/400/2000/4000 bieżących przypomnień. Nie jest to pusta
skrzynka managera. Odpowiedzi są limitowane20, raport zwraca pełne agregaty + podglądy.
Raw JSON zawiera próbki,min,max,payload bytes i fingerprinty zapytań.

| Salony | Strony po100 | Odczytane/unikalne | Całe przejście ms | Przypomnienia zapisane | Generowanie ms |
|---:|---:|---:|---:|---:|---:|
| 300 | 3 | 300/300 | 39.717 | 600 | 25.421 |
| 1000 | 10 | 1000/1000 | 194.261 | 2000 | 84.081 |
| 5000 | 50 | 5000/5000 | 2934.319 | 10000 | 769.199 |
| 10000 | 100 | 10000/10000 | 11549.028 | 20000 | 2566.500 |

Dane: Nsalonów,Ntasków,Nwizyt,2NActivity. Wizyty celowo jednoczesne do testu obciążenia
kolejki, nie deklaracja prawdziwych uzgodnień. Ostatnia partia generowania zwraca0;
unikalne klucze nie są ponownie oznaczane jako nowe wykonanie.20tys przypomnień przy
10tys salonów powstało w20partiach do1000 (500task+500visit). Czas to samo generowanie,
bez minutowych pauz harmonogramu. Planowanie follow-up ma osobny limit100/user/cykl;
nie przedstawiamy tego pomiaru jako czasu pełnego10tys planowania lub deliverySLA.

## EXPLAIN i przyczyny kolejnych pomiarów

1. Stara funkcja zffeabe0 pobierała cały zbiór:1501/5001/25001/50001SQL.
   Nie porównujemy jej czasu do jednej nowej strony jako identycznej operacji.
2. Pierwsza nowa wersja nadal używała tysięcy LATERAL/indexprobes. Po planie wykonania
   zastosowano zbiorczą kwalifikację, DISTINCTON i łączenia. Plany/pre-aggregate zachowane.
3. Skorygowano aktora pomiaru skrzynki (manager miał0 wpisów). pre-feed-role pokazuje
   wcześniejszy przebieg; te puste wyniki nie są końcową miarą skrzynki handlowca.
4. Wypełniona skrzynka ujawniła zły plan małych/średnich zbiorów:przy1000 salonów
   mediana1111.497ms, a plan wielokrotnie wyliczał UNION. Wyniki/plany zachowane w
   pre-notification-materialization. ScopedMATERIALIZED usuwa tę zmienność; końcowa
   tabela zawiera rzeczywiste wyniki po poprawce, także gdy któryś wariant był wolniejszy.
5. Odczyt referencyjnej starej funkcji nie był powtarzany przy samym strojeniu feeda;
   legacy_monitor jawnie wskazuje wcześniejszy plik pochodzenia. NoweAPI i paginację
   zmierzono ponownie po zmianie zapytania. Wszystkie dane pochodzą z lokalnych baz,
   które po pomiarze usunięto. Brak produkcyjnych danych/eksportów/restore.

EXPLAIN(ANALYZE,BUFFERS,FORMATJSON) zapisany dla contacts/tasks/visits/notifications
każdej wielkości. Szerokie odczyty mogą wybrać SeqScan/HashJoin; nie przypisujemy
wyników automatycznie dodatkowym indeksom007. Schemat007 jest opcjonalny i wymaga
osobnej zgody produkcyjnej. Wyniki nie potwierdzająRPO60 ani gotowościRender.
