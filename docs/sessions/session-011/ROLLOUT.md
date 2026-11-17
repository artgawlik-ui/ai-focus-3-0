# Rollout / kontrola procesów — plan, niewykonany

Warunki: osobna zgoda na konkretny SHA/deploy/zmianę flag, zielone CI, aktualne 004,
4 zatwierdzone SELECT-y, potwierdzone RPO60 i świeży uzgodniony punkt recovery,
trwały klucz/magazyn, potwierdzony artefakt rollbacku. Niespełnienie -> STOP.

## Pierwsze przejście ze starego kodu

1. Wszystkie Meta/DM/płatne AI OFF. Po osobnym zatwierdzeniu konfiguracji wdrożyć
   kandydat z WORKER_PAUSED=true. Nowy API może działać, ale nowy worker nie wykonuje
   jobów, Meta ani retencji. Nie używać AGENT_V2_ENABLED jako pauzy.
2. Stary d15265b nie zna pauzy ani blokad 010/011. Do czasu jego zakończenia nadal może
   pisać do bazy. Nie uznawać samych health/nowego PID za dowód zakończenia starej instancji.
   Odczytać zdarzenia zatrzymania starego deployu/procesów w Render i skontrolować kolejkę
   w zatwierdzonym kanale. Brak jednoznacznego potwierdzenia -> STOP, nowe workery w pauzie.
3. Przy ograniczeniu supervisora 25 s długie zadanie może zostać przerwane. Stan running
   odzyskuje się po 5 minutach. Nie wymuszać SQL status='queued'. Poczekać na brak starych
   procesów i rozliczyć każdą różnicę count/hash. API nadal może pisać: nie udawać okna
   bez zapisów, gdy właściciel/użytkownicy wykonują operacje.
4. Dopiero po potwierdzeniu zakończenia starego kodu i osobnej zgodzie wznowić nowy worker.
   WORKER_PAUSED=false wymaga zatwierdzonej zmiany konfiguracji/deployu; nie wykonał jej agent.
   Drugie przejście ma stary proces już w pauzie. Meta pozostaje OFF.
5. Kontrole: faktyczne SHA/deploy, API/DB health, lokalny worker status, świeżość heartbeat,
   kolejka, odzyskane zadania, brak nowych szkiców przy opt-out, 17 tabel/004/konta/SHA.
   Nowe API health nie potwierdza działania workera ani gwarancji recovery.

## Wyciszenie wersji znających mechanizm 011

WORKER_PAUSED=true lub lokalny plik /tmp/focus3-worker.pause. Plik jest lokalny dla
instancji i musi mieć kontrolowane uprawnienia; nie jest rozproszonym przełącznikiem.
Nie udostępniono endpointu WWW do jego zmiany. Zmiany na produkcji wymagają zgody.
Pauza działa na granicy etapów, nie przerywa bieżącej transakcji/HTTP; poczekać na
state=paused z nowym timestamp dla KAŻDEGO procesu. SIGTERM kończy bieżący etap i
nie zaczyna kolejnego; supervisor po 25 s wymusza kill. Nigdy nie obiecywać czasu drain
≤25 s dla HTTP do 60 s. Nie przyjmować nowych zadań operacyjnie w zatwierdzonym oknie.

Status /tmp/focus3-worker-status.json: state/pid/at, atomowy zapis, 0600, brak PII.
Sprawdzać lokalnie przez zatwierdzony kanał; brak publicznego endpointu procesu.
Proponowany alarm: brak/stary plik >120 s lub degraded/stopped bez planowanego stopu.
To próg operatorski do zatwierdzenia, nie wdrożony zewnętrzny monitoring/alerting.
Plik jest ulotny: nie zastępuje nadzoru Render ani trwałego audytu. Nie zmienia RPO.

## Zadania i rollback

Claim jest identyfikowany wartością updated_at wpisaną w transakcji przejęcia.
Przed finalizacją blokowany jest Job i sprawdzane running + dokładny claim timestamp.
Po przejęciu przez nowego wykonawcę poprzedni nie zapisze wyniku ANI failed.
Activity i completed commitują atomowo. Obejmuje wersje stosujące to sprawdzenie,
nie stary kod d15265b — dlatego wymagany kontrolowany pierwszy handoff.
Możliwa jest powtórna analiza/model call po przerwaniu; nie jest to exactly-once HTTP.
Płatny model nadal OFF, DM nieosiągalne. Brak nowej migracji, schemat 004 bez zmian.

Rollback do d15265b traci nowe zabezpieczenia. Najpierw wyciszenie/drain nowych workerów,
Meta OFF; osobna zgoda na rollback, potwierdzony artefakt/env. Nie cofać bazy ani nie
wznawiać starego i nowego wykonawcy jednocześnie. Po rollbacku nowe reguły nie obowiązują.
Brak migracji: nie wykonywać downgrade/DROP/restore. Stan danych porównać odczytowo.

## Recovery / RPO60

Odczyt 011 potwierdza PG17 available, 0.1c-256mb, 1 GB, Frankfurt, HA=false.
Dostępne get_postgres nie dostarcza latest recoverable timestamp/WAL lag/restore proof.
Nie utożsamiać available bazy ani historycznego PITR AVAILABLE z operacyjnym RPO60.
Najpierw wykorzystać obecny PITR: odczyt najnowszego osiągalnego punktu w Recovery lub
potwierdzenie providera przez właściciela. Potem osobno zatwierdzony izolowany test
recovery z dowodem wieku punktu ≤3600 s, bez przełączenia/overwrite produkcji.
Nie uruchamiać go teraz. Stary eksport i dzienny offsite nie spełniają RPO60.
Brak dowodu nie uzasadnia automatycznego zakupu większego planu.
