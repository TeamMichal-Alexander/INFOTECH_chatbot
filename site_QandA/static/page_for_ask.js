document.getElementById('answer').addEventListener('mouseup', function() {
    const selectedText = window.getSelection();
    const selection = selectedText.toString();
    const isSpecialCharSelected = /\s/.test(selection) && selection.trim() === '';

    if (selection.length > 0 && !isSpecialCharSelected) {
      console.log("Выделенный текст:", selection);
      // Получаем информацию о выделении
      const range = selectedText.getRangeAt(0);
      const rect = range.getBoundingClientRect();  // Получаем позицию выделенного текста

      // Проверка первого символа выделения
      const firstChar = selection.charAt(0);

      // Если выделение начинается с новой строки (например, при тройном клике), поднимем кнопку на одну строку выше
      if (firstChar === '\n') {
        // Сдвиг верхней границы на высоту первой строки
        rect.top += rect.height;
      }

      // Получаем элемент кнопки
      const button = document.getElementById('action-button');

      // Устанавливаем позицию кнопки
      button.style.position = 'absolute';
      button.style.left = `${rect.left + window.scrollX}px`; // По горизонтали
      button.style.top = `${rect.top + window.scrollY - 40}px`; // Над текстом (с небольшим отступом)
      button.style.zIndex = '9999';  // Чтобы кнопка была на переднем плане
      button.style.display = 'block'; // Показываем кнопку
    } else {
      // Если выделены только пробелы или спецсимволы, скрываем кнопку
      const button = document.getElementById('action-button');
      button.style.display = 'none';
    }
  });

  document.getElementById('answer').addEventListener('selectionchange', function() {
    const selectedText = window.getSelection();
    const selection = selectedText.toString();

    if (selection.length === 0) {
      const button = document.getElementById('action-button');

      button.style.display = 'none'; // Скрыть кнопку, если выделение пропало
    }
  });