# Propozycja retencji — wyłącznie podgląd, bez kasowania

Mechanizm: GET /api/focus-calendar/retention-preview, konto managera. Wynik to liczby
kandydatów, bez identyfikatorów klientów. Nie wykonuje DML/DDL ani operacji plikowych.
FOCUS_RETENTION_ENABLED=false jest zarezerwowane; nawet ustawienie true nie uruchamia
retencji. Kod nie zawiera endpointu wykonującego usunięcie. Każda przyszła realizacja
wymaga osobnego zatwierdzenia i testu odtwarzania.

| Kategoria | Domyślna propozycja | Obecne zachowanie |
|---|---|---|
| Przeczytane przypomnienia | 30 dni od utworzenia | tylko liczba kandydatów |
| Nieprzeczytane / nieaktualne przypomnienia | zachować do przeglądu | bez automatycznego usuwania |
| Wykonane zadania | przegląd archiwizacji po365 dniach od completed_at | zachować wynik i powiązanieCRM |
| Anulowane zadania | zachować do udokumentowania daty zamknięcia | brak zgadywania z created_at |
| Klienci, rzeczywiste kontakty i wizyty | brak automatycznego kasowania | nigdy nie są kandydatami |
| Plik statusu workera | wyłącznie aktualny stan, bez historii,0600 | istniejące atomowe nadpisanie |
| Audyt/API/security/Meta/Google/backupy | istniejące osobne zasady | bez zmian w tej sesji |

Archiwizacja nie oznacza fizycznego usunięcia rekordu ani jego FK. Bez zgody nie
usuwamy historii klienta ani wyników zadania; stare kopie mogą zawierać dawne dane,
więc przyszła polityka musi uwzględniać rejestr retencji przy odzyskiwaniu.
Nie udajemy włączonej automatycznej zgodnościRODO. Właściciel musi potwierdzić okresy,
podstawy prawne i ewentualne archiwum przed przygotowaniem wykonawcy retencji.
