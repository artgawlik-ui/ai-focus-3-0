# Minimalna zgoda A potrzebna do kontynuacji

To propozycja zakresu, NIE udzielona zgoda. Samo „wznów sesję 007” jej nie zastępuje.
Wymóg wynika z RESUME.md i komentarza właściciela:
https://github.com/artgawlik-ui/ai-focus-3-0/pull/3#issuecomment-6560668099

**Do zatwierdzenia:** wyłącznie SELECT-y z istniejącego pakietu
`docs/sessions/session-005/SELECTS.sql` / `scripts/release_selects.py` (commit 84e8bed),
w bazie Ai Focus 3.0 `dpg-dbh1b0gm7kps73f0p2m0-a`, przez zatwierdzony wewnętrzny
Shell/SSH istniejącej usługi `srv-dbh1rk6tlv9c73dloq20`.

Zakres: Alembic/PG/tabele, stan zatwierdzonych kont/sesji, liczności i SHA 17 tabel,
agregaty kolejki/inboxa/retencji. Brak treści klientów, haseł, tokenów i sekretów na wyjściu.
Transakcja REPEATABLE READ READ ONLY, timeouty, ROLLBACK; zero DML/DDL, eksportu,
restore/PITR, cleanup, restartu, deployu, aktywacji Meta i dodatkowych kosztów.
Tożsamości kont zatwierdza właściciel prywatnie; nie zgadywać po nazwie i nie wpisywać do raportu.

**Zgoda i kanał to dwie różne rzeczy.** Obecnie oba nie są zapewnione:
- nie ma pisemnej zgody A;
- publiczna allowlista jest pusta, a środowisko Codexa nie ma grantu TCP i VPN.

Po zgodzie A potrzebny istniejący, zatwierdzony Shell/SSH i ewentualny ograniczony grant
`ssh.frankfurt.render.com:22`, z weryfikacją host key. Nie otwierać bazy publicznie.
Nie tworzyć roli DB/klucza/network rules bez osobnej zgody; nie kopiować klucza prywatnego,
API key ani DATABASE_URL do rozmowy. Instrukcja techniczna:
`docs/sessions/session-003/ACCESS_RUNBOOK.md`.

Najpierw należy zatwierdzić A, potem zweryfikować/prowizjonować kanał w zatwierdzonym
zakresie. Samo „tak” nie konfiguruje sieci. Jeśli właściciel wybierze wykonanie we własnym
Render Shell, może użyć wariantu SELECTS.psql; nie musi wykonywać go ręcznie, gdy agent
otrzyma działający, autoryzowany kanał.

A nie obejmuje nowej kopii, dostępu do wartości kluczy, testowej recovery DB ani merge/deploy.
Propozycja PITR za około 0,20 USD/24h nadal NIE jest zatwierdzona; wycena wymaga
odświeżenia przed ewentualną osobną decyzją.
