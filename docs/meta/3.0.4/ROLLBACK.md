# Plan wycofania — bez wykonania na produkcji

Punkt odniesienia: d15265b26524d594bdbcb4bc6b63fcbc398a1424, live deploy dep-dbjhl6jbc2fs73crj65g. Autodeploy off, jedna istniejąca instancja, bez ingerencji w Focus 1.0/2.0.

1. Po zgodzie właściciela jawnie wyłączyć wszystkie flagi Meta, w tym każdą flagę modułu. Samo META_ENABLED=false nie wyłączy jawnych override true. DM zawsze false. Zachować klucz Fernet i dane.
2. Nie ma nowej migracji w 3.0.4: schemat pozostaje 004, nie wykonywać downgrade/DROP. Inbox, dedup keys i CRM pozostają. Trwające processing odzyskają się po wygaśnięciu dzierżawy dopiero po ponownym świadomym uruchomieniu odbioru/przetwarzania.
3. Po zgodzie wrócić do zapisanego deployu/commita 3.0.3. Dostępność artefaktu rollbacku trzeba potwierdzić w Render; listing historycznych deployów nie dowodzi retencji obrazu. Awaryjna ścieżka: zatwierdzony standardowy rebuild dokładnego commita, z flagami wyłączonymi.
4. Render rollback odzyskuje też zmienne środowiskowe z docelowego deployu, podczas gdy env groups mogą pozostać aktualne. Sprawdzić efektywne flagi oraz autodeploy po operacji, nie zakładać ich stanu. Dokumentacja: https://render.com/docs/rollbacks (sprawdzono 2026-11-01).
5. Sprawdzić HTTPS, health 3.0.3 i faktyczny commit, API bez sesji 401, webhook/OAuth 404, logi i odczytowy fingerprint po rollbacku. Żadnych testów zapisu na produkcyjnych klientach.
6. Cofnięcie kodu nie przywraca celowo usuniętego tekstu (unsend) ani innych zmian danych. Nie odtwarzać go z backupu w celu obejścia usunięcia. Nie nadpisywać produkcji starą kopią bez osobnej decyzji o danych nowszych od kopii i o usunięciach RODO.
7. PITR to osobna procedura danych: tworzy nową instancję i może wymagać dodatkowego kosztu. Wyłącznie po zgodzie, najpierw walidacja odzyskanej kopii i porównanie danych, potem osobny zatwierdzony cutover. W tym zadaniu PITR i rollbacku produkcji nie uruchomiono.

Historyczny zaszyfrowany eksport odtworzono lokalnie; wszystkie manifestowe SHA-256/liczby zgodziły się. Po testowych migracjach zachowano 9 starych tabel danych. To dowód działania procedury dla starego artefaktu, nie dowód aktualnego RPO/RTO produkcji. Świeży eksport, aktualny fingerprint i aktualne okno PITR pozostają warunkami blokującymi.
