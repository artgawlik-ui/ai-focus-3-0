# Wznowienie — ręczne przekazywanie zadań, Issue #7

Repo: artgawlik-ui/ai-focus-3-0.
Gałąź: `docs/issue-7-manual-codex-workflow`, z main d15265b26524d594bdbcb4bc6b63fcbc398a1424.
Przeczytaj `docs/reports/MANUAL_CODEX_WORKFLOW.md` i `docs/workflows/MANUAL_CODEX.md`.
To osobna gałąź; nie zmienia PR #3, PR #6 ani punktów wznowienia ich gałęzi.

Issue #7 utworzył właściciel; GitHub odczyt permission=admin. Bieżącą sesję Codexa
uruchomił właściciel ręcznie, zlecając odczyt Issue. Dokumentacyjny rezultat powstał
naprawdę, bez API OpenAI i bez symulacji wykonawcy. Końcowe push/Draft PR/CI oraz raport
w Issue należy potwierdzić przed PASS. Osobnej niezależnej oceny przez Fokus nie obserwowano.

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
