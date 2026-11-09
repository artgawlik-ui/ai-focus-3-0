# Kryteria027 — bez operacji produkcyjnych

1. Potwierdzić HEAD/CI PR #3 oraz niezmienione PR #6/#8; zachować prywatne ZIP-y.
2. Sprawdzić transport bez prób SSH przy pustym grancie. Tylko potwierdzony kanał,
   host i prywatne konta umożliwiają dokładnie4SELECT005 w jednym READ ONLY REPEATABLE READ.
3. Odczytać dostępne metadane recovery; nie utożsamiać available bazy z PITR/RPO.
4. Wprowadzić osobny opt-in profil awaryjny007: tylko odczyt, bez bootstrapu,
   migracji, workerów, integracji i nowego logowania. Normalny Dockerfile/start bez zmian.
5. Testy syntetyczne: realny API/PG17/007 i sesje/RBAC; serwer odrzuca SQL UPDATE;
   count/SHA21tabel bez zmian; błędne004/006 odrzucone. To nie test rollbacku Render.
6. Przygotować handoff ze STOPami, odróżniając public maintenance, pauzę workera
   i pełne zamrożenie bazy. Zdefiniować testy produkcyjne wyłącznie do późniejszej zgody.
7. Pełne CI nowego SHA: regresja, build, Chromium/WebKit i oba audyty. Nie zamykać
   brakujących bramek produkcyjnych na podstawie testów syntetycznych.
