# Silnik kwalifikacji fazy 2

Domyślne koszty dodatkowe: 0 USD. Silnik reguł działa lokalnie. AGENT_V2_ENABLED pozwala wyłączyć rozszerzoną punktację bez zmiany schematu. Nigdy nie zmienia sam priorytetu, etapu ani wizyty i nie wysyła wiadomości.

Wersja reguł glogow-b2b-1: maksymalnie 100 punktów. Specjalizacja zapisana w CRM +20 (sam fakt uzupełnienia, nie potwierdzenie jakości), deklarowany potencjał miesięczny >=3000 PLN +40, >=1500 +25, >0 +10; etap oferta/negocjacje +25, rozpoznanie +15; Głogów +15. A+ >=80, A >=60, B >=30, pozostałe C. To jawna heurystyka do walidacji przez menedżera, nie model przewidujący zakupy. Brak informacji nie jest zastępowany wymyślonym faktem. Okolice Głogowa wymagają ręcznej kwalifikacji — brak obliczania odległości.

Każde kryterium ma identyfikator źródła CRM, a wynik wersję reguł, datę, wykaz braków i źródła z datą pozyskania rekordu. Swobodny tekst operatora jest oznaczony jako niezweryfikowany i nie zwiększa punktacji. Historia jest odczytywana przed analizą, kontakt z ostatnich 7 dni powoduje rekomendację odczekania. Wynik i źródła pozostają w job.result, historia zawiera wpis agent_draft. Nie wykonuje się automatycznego importu nowych leadów.

Odpowiedzi email_received otrzymują jedynie etykiety do przeglądu: możliwa rezygnacja, możliwe zainteresowanie wizytą, przegląd ręczny. To proste dopasowania fraz, nie pełne rozumienie języka; możliwe błędne alarmy i pominięcia. Możliwa rezygnacja blokuje szkic, ale nie zmienia danych CRM bez właściciela. Brak monitorowania skrzynki/Instagram; odpowiedź wprowadza operator. Propozycja wizyty nakazuje sprawdzić dostępność — nie tworzy ani nie rezerwuje terminu.

## Opcjonalny dostawca AI — nieaktywny

OpenAI API, gpt-4.1-mini. Oficjalna karta modelu odczytana 2026-10-28: 0,40 USD / 1 mln tokenów wejścia, 0,10 cache, 1,60 wyjścia (standard; bez narzędzi). Przykład: 1000 analiz po 400 tokenów wejścia i 300 wyjścia = ok. 0,64 USD, przed podatkami i kursem walut. To kalkulacja, nie zatwierdzony budżet ani gwarancja zużycia/ceny. Model może zmienić dostępność; realnego wywołania nie wykonano.

Źródło: https://developers.openai.com/api/docs/models/gpt-4.1-mini . Zasady: https://platform.openai.com/docs/guides/your-data — dane API domyślnie nie służą treningowi; logi abuse monitoring mogą być przechowywane do 30 dni, z wyjątkami prawnymi/bezpieczeństwa. store=false nie oznacza Zero Data Retention. ZDR wymaga odrębnego zatwierdzenia; rezydencja, DPA i mechanizm transferu danych wymagają weryfikacji w projekcie dostawcy. Nie deklarujemy rezydencji UE bez jej konfiguracji.

Adapter po odrębnej zgodzie AI_PAID_PROCESSING_APPROVED=true i bezpiecznej konfiguracji OPENAI_API_KEY przekazuje tylko punktację, priorytet, wersję reguł i nazwy brakujących pól. Nie wysyła danych kontaktowych, nazw, notatek, odpowiedzi ani materiałów źródłowych. Zwraca niezweryfikowane neutralne pytania; model nie nadpisuje punktacji, szkicu ani CRM. Limit wyjścia 300 tokenów; brak automatycznych ponowień wywołania. Sam klucz API nie aktywuje kosztów. Testy API wykorzystują wyłącznie atrapy transportu na syntetycznych danych.
