# Kryteria 012

- Odczyt HEAD/CI/grantu i metadata bez SSH przy pustym grancie, bez operacji produkcyjnych.
- Rzeczywiste procesy starego d15265b i nowego workera na syntetycznym PG17: pause, SIGTERM/kill, wznowienie, jeden szkic.
- Uruchomienie starego API na obecnym schemacie nie zmienia fingerprintów 17 tabel.
- Nieudany start supervisora nie pozostawia API; test na prawdziwych procesach.
- API odmawia kolejki dla zapisanej rezygnacji klienta, bez utworzenia Job.
- Pełne końcowe CI, PR Draft, raport i RESUME; bez merge/deploy/produkcji.
