# Kopie i odtwarzanie

Narzędzie: `python -m scripts.backup backup /bezpieczny/katalog/focus3.enc`.
Wymaga PostgreSQL 17 client, `DATABASE_URL` i osobnego `BACKUP_PASSPHRASE` (20+ znaków) w bezpiecznym magazynie. Format: pg_dump custom zaszyfrowany AES-256-GCM; klucz wyprowadzany przez scrypt z losową solą. Plik ma uprawnienia 0600. Hasło nie jest wypisywane ani zapisywane w repozytorium.

Na czas dumpa i manifestu utrzymywana jest krótka blokada zapisu tabel; odczyty pozostają dostępne. Zablokowane zapisy czekają. `lock_timeout=5s`, timeout pg_dump=120s. Dla większej bazy należy uzgodnić okno serwisowe i monitorować czas blokady.

Kopię przenieś do prywatnego magazynu poza usługą Render, z szyfrowaniem i retencją. Sekret klucza przechowuj oddzielnie. Automatyczny harmonogram/offsite nie jest skonfigurowany bez wskazania magazynu i bezpiecznego dostępu. Sam plik na efemerycznym dysku usługi nie jest trwałą kopią.

Odtwarzanie: utwórz NOWĄ pustą bazę, ustaw `RESTORE_DATABASE_URL` i `BACKUP_PASSPHRASE`, a następnie `python -m scripts.backup restore /ścieżka/focus3.enc`. Narzędzie odmawia pracy na źródłowym adresie bazy i na każdym niepustym celu. Używa transakcyjnego pg_restore bez opcji clean/drop. Porównuje liczby i SHA-256 znormalizowanej zawartości wszystkich tabel aplikacji. Rozbieżność oznacza nieudane sprawdzenie.

Po zgodnym odtworzeniu sprawdź logowanie, wybrane salony, historię i wizyty w osobnym środowisku. Nie przekierowuj produkcji bez decyzji administratora. Przywrócone sesje należy unieważnić przed udostępnieniem środowiska odtworzeniowego innym osobom.

Test 2026-10-28: PostgreSQL 17, syntetyczne dane CRM, sesje i historia; szyfrowanie → odtworzenie do oddzielnej bazy → zgodność liczebności i skrótów. Powtórne odtworzenie do niepustego celu prawidłowo odrzucone. Nie wykonano kopii ani migracji Focus 1.0/2.0; ich źródło produkcyjne nie zostało zweryfikowane.

Docelowy harmonogram: codzienna kopia poza hostem, retencja 30 dni, cotygodniowe odtworzenie testowe i alert o niepowodzeniu. To wymaganie operacyjne, a nie już aktywna usługa.
