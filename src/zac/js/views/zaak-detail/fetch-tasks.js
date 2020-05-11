import { apiCall } from '../../utils/fetch';


const enableButtons = () => {
    const actionLinks = document.querySelectorAll('.page-controls .link--disabled');
    Array.from(actionLinks).forEach(node => {
        node.classList.remove('link--disabled');
    });
};


const checkEnableAfhandelButton = (node) => {
    const userTasks = node.querySelectorAll('.user-task');
    // if there are user tasks, you cannot use the buttons directly
    if (userTasks.length) {
        return;
    }
    enableButtons();
};


const fetchTasks = (node) => {
    const { url, forZaak } = node.dataset;

    const fullUrl = `${url}?zaak=${forZaak}`;
    apiCall(fullUrl)
        .then(response => response.text())
        .then(content => {node.innerHTML = content;})
        .then(() => checkEnableAfhandelButton(node))
        .catch(console.error);
};

const nodes = document.querySelectorAll('.fetch-tasks');
// there could be a lack of permissions, causing the buttons to stay disabled. If there
// are permissions to handle case, the buttons should be activated.
if (!nodes.length) {
    enableButtons();
} else {
    Array.from(nodes).forEach(fetchTasks);
}
