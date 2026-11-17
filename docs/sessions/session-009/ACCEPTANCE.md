# Kryteria sesji 009

- Awaria opcjonalnego AI zachowuje wynik regułowy; brak sekretów w błędach i logach.
- Bez obu warunków zgody i klucza nie ma HTTP do modelu.
- Przed zapisem szkicu worker ponownie odczytuje uprawnienia oraz blokadę kontaktu.
- Testy jednostkowe na mockach, bez bazy/realnych usług; CI dokładnego SHA sprawdzone.
- Bez zmiany flag, schematu, Meta, produkcji, merge/deploy; PR Draft.
