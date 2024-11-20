document.getElementById('answer').addEventListener('mouseup', display_button);
document.getElementById('answer').addEventListener('touchend', display_button);

function display_button() {
    setTimeout(() => {
        const selectedText = window.getSelection();
        const selection = selectedText.toString();
        const isSpecialCharSelected = /\s/.test(selection) && selection.trim() === '';
        console.log(selection.length)
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
    }, 20);
}

document.getElementById('answer').addEventListener('selectionchange', function () {
    const selectedText = window.getSelection();
    const selection = selectedText.toString();

    if (selection.length === 0) {
        const button = document.getElementById('action-button');
        const form_improve = document.getElementById('form_improve');

        button.style.display = 'none'; // Скрыть кнопку, если выделение пропало
        form_improve.style.display = 'none'
    }
});


document.getElementById('action-button').addEventListener('click', function () {
    const quotation_text = document.getElementById('quotation_text');
    const quotation = document.getElementById('quotation');
    const button = document.getElementById('action-button');
    const selectedText = window.getSelection();
    const cleanedText = String(selectedText).replace(/\n/g, " ");
    const range = selectedText.getRangeAt(0);
    const selectedNode = range.commonAncestorContainer;

    console.log(selectedNode.nodeType === 3
        ? selectedNode.parentElement.closest('.UserAnswer')
        : selectedNode.closest('.UserAnswer'));
    // Находим ближайший div с классом UserAnswer
    sessionStorage.setItem('quotation_div', selectedNode.nodeType === 3
        ? selectedNode.parentElement.closest('.UserAnswer')
        : selectedNode.closest('.UserAnswer').innerHTML);
    // form_improve.style.position = 'absolute';
    // form_improve.style.left = button.style.left
    // form_improve.style.top = button.style.top
    const reply_symbol_quotation = document.getElementById('quotation_symbol');
    const delete_quotation = document.getElementById('delete_quotation');


    reply_symbol_quotation.style.display = 'block';
    delete_quotation.style.display = 'block';
    quotation.style.display = 'block';
    setTimeout(() => {
        quotation.style.height = '40px';
    }, 50);

    setTimeout(() => {
        quotation_text.innerText = cleanedText;
    }, 150);
    button.style.display = 'none';
    clearSelection();
    // form_improve.style.zIndex = '10000';
    // form_improve.style.display = 'block'
});

function delete_quotation(){
    const quotation_text = document.getElementById('quotation_text')
    const quotation = document.getElementById('quotation')
    const reply_symbol_quotation = document.getElementById('quotation_symbol');
    const delete_quotation = document.getElementById('delete_quotation');


    reply_symbol_quotation.style.display = 'none';
    delete_quotation.style.display = 'none';
    quotation_text.innerText = '';
    quotation.style.height = '0';
    setTimeout(() => {
        quotation.style.display = 'none';
    }, 300);
}

function clearSelection() {
    if (window.getSelection) {
        const selection = window.getSelection();
        if (selection) {
            selection.removeAllRanges(); // Удаляет все выделенные диапазоны
        }
    } else if (document.selection) { // Для старых браузеров (IE)
        document.selection.empty();
    }
}

document.addEventListener('DOMContentLoaded', function() {
        const text = "Cześć użytkowniku";
        const element = document.getElementById('h1_text');
        console.log(1);
        for (let i = 0; i < text.length; i++) {
            setTimeout(() => {
                element.textContent += text.charAt(i);
            }, 75 * i);
        }
    });


function expandContainer() {
    const formContainer = document.querySelector('.panel');
    if (window.innerWidth > 650) {
        formContainer.classList.add('expanded');
    }
}

function collapseContainer() {
    const formContainer = document.querySelector('.panel');
    const inputField = document.querySelector('#query');
    const submitButton = document.querySelector('#button_submit_form');

    setTimeout(() => {
        if (!document.activeElement.isSameNode(inputField) && !document.activeElement.isSameNode(submitButton)) {
            formContainer.classList.remove('expanded');
        }
    }, 100);
}

document.querySelector('#query').addEventListener('focus', expandContainer);

// Когда фокус уходит с input, проверяем, не фокусируется ли кнопка
document.querySelector('#query').addEventListener('blur', collapseContainer);

// Когда фокус на кнопке, увеличиваем ширину контейнера
document.querySelector('#button_submit_form').addEventListener('focus', expandContainer);

// Когда фокус уходит с кнопки, проверяем, не фокусируется ли input
document.querySelector('#button_submit_form').addEventListener('blur', collapseContainer);