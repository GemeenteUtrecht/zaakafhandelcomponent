const SELECTOR = '.checkbox-select.checkbox-select--dynamic';


const getOptionsHtml = (name, options, selectedValues) => {
    const valueSet = new Set(selectedValues);
    const htmlBits = options.map(([value, display], index) => {
        const id = `id_${name}_${index}`;
        return `
            <li class="checkbox-select__option">
                <input
                    type="checkbox"
                    name="${name}"
                    id="${id}"
                    value="${value}"
                    ${valueSet.has(value) ? 'checked' : ''}
                >
                <label for="${id}">${display}</label>
            </li>`;
    });
    return htmlBits.join('\n');
};

const checkboxSelect = (node) => {
    const { name, listen, values, initial } = node.dataset;
    const options = JSON.parse(document.getElementById(values).innerText);
    const initials = JSON.parse(document.getElementById(initial).innerText);
    const showOptions = (group, values) => {
        const markUp = getOptionsHtml(name, options[group] || [], [values]);
        node.innerHTML = markUp;
    };

    const catalogus = document.getElementById(listen);

    catalogus
        .addEventListener('change', (e) => showOptions(e.target.value, []));

    const selectedValue = (catalogus.querySelector('[checked]') || []).value;
    showOptions(selectedValue, initials);
};


Array.from(document.querySelectorAll(SELECTOR)).forEach(node => checkboxSelect(node));
