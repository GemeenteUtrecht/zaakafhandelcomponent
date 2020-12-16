const showTab = (containerNode, tab, event) => {
    event.preventDefault();

    const targetTabId = tab.getAttribute('aria-controls');

    // mark all other tabs as not active
    const tabNodes = containerNode.querySelectorAll('.tab__tab');
    const paneNodes = containerNode.nextElementSibling.querySelectorAll('.tab__pane');

    for (const tabNode of tabNodes) {
        const show = tabNode.getAttribute('aria-controls') === targetTabId;
        tabNode.classList.toggle('tab__tab--active', show);
    }
    for (const paneNode of paneNodes) {
        const show = paneNode.id === targetTabId;
        paneNode.classList.toggle('tab__pane--active', show);
    }
};


const initTab = (node) => {
    // register event handlers
    const tabs = node.querySelectorAll('.tab__tab');
    for (const tab of tabs) {
        tab.addEventListener('click', showTab.bind(this, node, tab));
    }
};


// run by default
const tabNodes = document.querySelectorAll('.tab');
for (const tabNode of tabNodes) {
    initTab(tabNode);
}

export { initTab };
