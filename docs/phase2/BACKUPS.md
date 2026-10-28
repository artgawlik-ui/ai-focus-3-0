# Kopie fazy 1

Punkt przywracania: 0c44401d2b8ef2b7d11813e35aed69ab3b0de6fe / dep-dbh4jsd9el5s73ap7n50. Brak zmian schematu w fazach 1–2.

Przed zmianą hasła właściciela pobrano nową zaszyfrowaną kopię istniejącej bazy; hasło zmienia wyłącznie właściciel w Ustawienia → Bezpieczeństwo konta. Nie zmieniono jego hasła i nie dodano konta. Hash Argon2id, minimum 12 znaków, zalecana unikalna fraza 16+ znaków z menedżera haseł, 8 błędnych logowań/15 min; zmiana wymaga starego hasła i unieważnia inne sesje. MFA nie jest zaimplementowane; MFA Render nie chroni automatycznie loginu CRM.

Zaimplementowano opcjonalny proces `python -m scripts.offsite_backup`: raz dziennie szyfruje pg_dump, przesyła przez HTTPS i AWS Signature V4 do skonfigurowanego magazynu S3, ponawia po błędzie po godzinie. Działa w istniejącej usłudze, bez dodatkowego Render cron. Bez konfiguracji pozostaje wyłączony. Klucz IAM powinien pozwalać tylko PutObject dla dedykowanego prefiksu; wersjonowanie, blokadę publicznego dostępu, region UE i lifecycle 30 dni konfiguruje administrator magazynu. Obiekty z wersjonowaniem wymagają też reguły usuwania wersji nieaktualnych. Nie ma uprawnień kasowania ani odtwarzania produkcji.

W Render Environment skonfigurować bezpiecznie dopiero po akceptacji magazynu i kosztu: BACKUP_S3_PREFIX_URL, BACKUP_S3_REGION, BACKUP_S3_ACCESS_KEY_ID, BACKUP_S3_SECRET_ACCESS_KEY, BACKUP_PASSPHRASE (osobny sekret 20+ znaków), BACKUP_RETENTION_CONFIRMED_DAYS=30, OFFSITE_BACKUP_ENABLED=true. Nie przekazywać tych wartości w rozmowie. Potwierdzenie lifecycle jest deklaracją operatora, nie kontrolą API magazynu.

Status: lokalne szyfrowanie/odtwarzanie przetestowane; harmonogram i podpisany upload przygotowane. Zdalny magazyn, realny upload, jego lifecycle i alert do właściciela nie są zweryfikowane ani aktywne. Koszt magazynu i operacji zależy od wybranego dostawcy; nie zaakceptowano żadnego nowego kosztu. Aktualna baza nadal korzysta z udokumentowanego Render PITR; dodatkowej instancji odtwarzania nie tworzono.

Odtwarzanie: docs/RECOVERY.md. Co tydzień odtworzyć kopię do odizolowanej pustej bazy, porównać wszystkie liczebności/SHA-256 i sprawdzić CRM na danych syntetycznych. Nigdy nie nadpisywać istniejącej produkcji. Nie udostępniać odtworzonych sesji. Rollback kodu nie przywraca danych; przed przełączeniem źródła danych wymagana decyzja właściciela.
