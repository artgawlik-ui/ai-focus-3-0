# Sesja018 — domknięcie ergonomii i bezpieczeństwa natywnego planera

- Oddzielny przełącznik schematu i funkcji: wyłączenie funkcji po006 nie uniemożliwia startu.
- Termin datetime-local interpretowany jawnie w Europe/Warsaw; luka DST odrzucana,
  dwuznaczna godzina wymaga wyboru wystąpienia. Stary ISO nadal zgodny.
- Powiadomienie wizyty aktualne i pojedyncze, nie pokazuje przeszłej/odwołanej wizyty.
- Blokada rekordu salonu serializuje generowanie z równoległą zmianą opt-out.
- Testy syntetyczne, bez produkcji i Google; pełny CI i raport poranny.
