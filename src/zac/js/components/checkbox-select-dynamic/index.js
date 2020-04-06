const SELECTOR = '.checkbox-select.checkbox-select--dynamic';


const getOptionsHtml = (name, options) => {
    const htmlBits = options.map(([value, display], index) => {
        const id = `id_${name}_${index}`;
        return `
        <li class="checkbox-select__option">
            <input type="checkbox" name="${name}" id="${id}" value="${value}">
            <label for="${id}">${display}</label>
        </li>`;
    });
    return htmlBits.join("\n");
};


const checkboxSelect = (node) => {
    const { name, listen, values } = node.dataset;
    const options = JSON.parse(document.getElementById(values).innerText);

    document
        .getElementById(listen)
        .addEventListener('change', (e) => {
            const markUp = getOptionsHtml(name, options[e.target.value]);
            node.innerHTML = markUp;
        });
};


Array.from(document.querySelectorAll(SELECTOR)).forEach(node => checkboxSelect(node));
