import { apiCall } from '../../utils/fetch';


const checkEnableAfhandelButton = (node) => {
    const userTasks = node.querySelectorAll('.user-task');
    // if there are user tasks, you cannot use the buttons directly
    if (userTasks.length) {
        return;
    }

    const actionLinks = document.querySelectorAll('.page-controls .link--disabled');
    Array.from(actionLinks).forEach(node => {
        node.classList.remove('link--disabled');
    });
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
Array.from(nodes).forEach(fetchTasks);
