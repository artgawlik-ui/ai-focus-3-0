# Runbook dostępu — przygotowany, niewykonany

Cel: odczytać wyłącznie agregaty/zbieżność zatwierdzonego manifestu w istniejącej usłudze.
Bez publicznej allowlisty PostgreSQL, nowej usługi i endpointu SQL.

## Warunki wejścia / STOP

1. Właściciel osobno zatwierdza zakres A z DECISIONS.md. Sama sesja 003 nie jest zgodą.
2. Render Dashboard → **Account settings → SSH Public Keys → + Add SSH Public Key**:
   publiczna część zatwierdzonego klucza; prywatna w zatwierdzonym magazynie/agentcie.
   Nie generować ulotnego klucza bez uzgodnionej trwałości. Nie przesyłać sekretu do Codex.
3. Administrator środowiska dopuszcza tylko TCP `ssh.frankfurt.render.com:22`.
   W odczytanej polityce domains/ip_ranges są puste, VPN false; dostępu nie próbowano.
4. Zweryfikować klucz hosta Render z zaufanego kanału, następnie przypiąć go w known_hosts.
   Sam ssh-keyscan nie uwierzytelnia hosta. Nie stosować StrictHostKeyChecking=no,
   automatycznego accept-new ani alternatywnego tunelu jako obejścia polityki.
5. Render → istniejąca usługa **ai-focus-3-0 → Connect → SSH**: ponownie odczytać adres.
   Historyczny adres: `srv-dbh1rk6tlv9c73dloq20@ssh.frankfurt.render.com`; nie traktować
   go jako bieżącego potwierdzenia usługi/regionu/uprawnień. Bez shell roota i eskalacji sudo.

Po zatwierdzeniu i weryfikacji kluczy przykład logowania (NIEWYKONANY):

```sh
ssh -o BatchMode=yes -o StrictHostKeyChecking=yes \
  -i "$APPROVED_SSH_KEY_PATH" \
  srv-dbh1rk6tlv9c73dloq20@ssh.frankfurt.render.com
```

Klucz konta Render może dawać więcej uprawnień niż sam odczyt SQL: nie deklarujemy,
że SSH jest mechanizmem RBAC read-only. Ograniczenie polega na zatwierdzonym narzędziu,
transakcji READ ONLY i zakresie czynności; potrzebę dedykowanego DB read-only role
należy rozpatrzyć osobno (utworzenie roli zmienia produkcję, teraz zabronione).
Nie wyświetlać env, URL, listy sekretów, ssh -vv ani zawartości pliku klucza.

## Wykonanie preflightu — dopiero po zgodzie

Kod obecnej produkcji może nie zawierać modułu. **Nie deployować gałęzi w celu jego dostarczenia.**
Osobno zatwierdzić transfer wyłącznie przypiętych wersji scripts/readonly_preflight.py
oraz scripts/salon_cleanup.py i manifestu do prywatnego katalogu narzędziowego.
Sprawdzić sumy zatwierdzonych plików bez ujawniania manifestu. Nie instalować pakietów,
nie uruchamiać backend.main, migracji, bootstrapu, aplikacji i workerów.
Jeśli brakuje psycopg lub dostępu do modułów, STOP; nie modyfikować produkcyjnego runtime.
Wewnętrzny DATABASE_URL ma pozostać wyłącznie w już istniejącym środowisku procesu.

```sh
python -m scripts.readonly_preflight \
  --manifest "$APPROVED_MANIFEST_PATH" \
  --approved-internal-readonly
```

Identyfikatory dla `--technical-user-id` i `--owner-user-id` dopiero po jednoznacznym
zatwierdzeniu, bez zgadywania po nazwie. Nie wpisywać ich w publiczny log poleceń.
Narzędzie nie zapisuje danych i zawsze kończy ROLLBACK. Timeouty: connect 5 s,
statement 5 s, lock 1 s, idle transaction 10 s; jedna transakcja, bez puli i zadania w tle.

Oczekiwany output: status PASS lub BLOCKED; scope_matches, schema_matches, listy
nazw rozbieżnych kontroli; scope_counts i scope_total; transaction_read_only=true,
isolation=repeatable read, public_table_count=17, postgres_major=17;
stan owner_account/technical_account PASS/BLOCKED/not_checked. Brak ID/PII/tokenów/hashów treści.
PASS zakresu nie potwierdza świeżości backupu ani uprawnień do cleanup/deploy.
`production_state_claimed=false` oznacza brak deklaracji pełnej gotowości produkcji.

STOP: brak zgody/grantu, nieznany host key, inny host/baza/PG major/revision, timeout,
brak manifestu, różnica dowolnego hash/ID/liczby/schematu, aktywny job/Meta link,
nieznane konta/sesje lub output BLOCKED. Nie poprawiać manifestu automatycznie;
nie wykonać DELETE ani COMMIT; zachować tylko zanonimizowany wynik do przeglądu.
Historyczny zakres 13 rekordów wymaga świeżego potwierdzenia.

Źródła instrukcji: https://render.com/docs/ssh (sprawdzone w sesji 002), bieżący kod
preflightu i najnowszy komentarz właściciela w PR #3. Panel i klucze niezweryfikowane.
