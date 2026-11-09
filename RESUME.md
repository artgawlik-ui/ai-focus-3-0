# Wznowienie — ręczne przekazywanie zadań, Issue #7

Repo: artgawlik-ui/ai-focus-3-0.
Gałąź: `docs/issue-7-manual-codex-workflow`, z main d15265b26524d594bdbcb4bc6b63fcbc398a1424.
Przeczytaj `docs/reports/MANUAL_CODEX_WORKFLOW.md` i `docs/workflows/MANUAL_CODEX.md`.
To osobna gałąź; nie zmienia PR #3, PR #6 ani punktów wznowienia ich gałęzi.

Issue #7 utworzył właściciel; GitHub odczyt permission=admin. Bieżącą sesję Codexa
uruchomił właściciel ręcznie, zlecając odczyt Issue. Dokumentacyjny rezultat powstał
naprawdę, bez API OpenAI i bez symulacji wykonawcy. Potwierdzono push7f880960b34bbcc0fee47693ea030bb9998b06c0, Draft PR #8,
pełne CI push42708132895/PR42708200556SUCCESS:80PASS/2warnings,build,Chromium/WebKit
i audyty PASS (0znanych podatności). Raport Issue #7:comment6752742954 zapisany.
Ostatni dopisek dokumentacyjny/placeholder YAML wymaga odczytu własnych Checks;
końcowy SHA i wynik są publikowane w komentarzu Issue #7 i opisie PR #8. Osobnej niezależnej oceny przez Fokus nie obserwowano.

Dostarczono instrukcję, formularz Issue, krótki prompt, nieszkodliwy artefakt i link README.
Nie dodano executorów/workflow/schedulerów/kluczy/nowych kosztów. Automatyzacja pozostaje
niezainstalowana na main i bez aktywacji; nie zmieniano flag lub konfiguracji PR #6.
Znana korekta wyłącznie istniejącego testu: zegar120/179.9/180s zamiast uptime hosta.
Nie powtarzać diagnostyki z026; nie zmieniono runtime, timeoutów i skipów.

Zakazy: bez merge/deployu, produkcji/Render/SQL/migracji/restore/eksportu/kasowania,
sekretów, Meta/DM/Google i zmian Focus1.0/2.0. PR #3 i #6 pozostają Draft i bez zmian.
Brak klucza OpenAI nie blokuje ręcznego procesu; ograniczenia planu/autoryzacji Codexa
lub GitHub mogą wymagać działania właściciela. Nie prosić o sekrety w rozmowie.

Przy wznowieniu sprawdź aktualny HEAD i CI dokładnego SHA oraz raport Issue #7.
Nie zaczynaj ponownie wykonanej dokumentacji i nie uruchamiaj dwóch sesji dla jednego
zadania. Kolejne rutynowe zadanie dopiero po odczycie nowego Issue lub decyzji właściciela.

Ręczny proces jest przetestowany w tej sesji; brak niezależnego końcowego przeglądu
przez osobną instancję Fokus nie został ukryty ani zasymulowany. Nie przenosić statusu
PASS na API-owy wykonawca PR #6 lub na produkcyjne wydanie. Formularz można czytać
z gałęzi; jego instalacja na main wymaga oddzielnej zgody, nie jest potrzebna
do używania zwykłego Issue i krótkiego promptu teraz. Bez nowych metod testowych.
