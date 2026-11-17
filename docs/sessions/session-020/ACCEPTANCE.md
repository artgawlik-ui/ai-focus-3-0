# Sesja020 — historia i transakcyjne odzyskiwanie

- Zmiana terminu zadania zapisuje stare i nowe wartości oraz użytkownika.
- SIGKILL natywnego tick przed commitem nie pozostawia częściowych zadań/aktwności;
  nowy tick odtwarza zadania raz, nie tworzy fikcyjnych kontaktów.
- Błąd nowego tick nie ujawnia treści wyjątku i nie oznacza sukcesu.
- Syntetyczny PostgreSQL, bez realnych operacji; regresja i pełny CI/Draft.
