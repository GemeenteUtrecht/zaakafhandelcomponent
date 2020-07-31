import React from 'react';
import ReactDOM from 'react-dom';

import { ProcessInteraction } from './ProcessInteraction';

const CLASS_NAME = 'process-interaction';


const init = () => {
    const nodes = document.querySelectorAll(`.${CLASS_NAME}`);
    for (const node of nodes) {
        const props = {
            zaak: node.dataset.zaak,
            endpoint: node.dataset.endpoint,
            // convert to actual bools
            canDoUserTasks: node.dataset.canDoUserTasks === "true",
            canSendBpmnMessages: node.dataset.canSendBpmnMessages === "true",
        };
        ReactDOM.render(<ProcessInteraction {...props} />, node);
    }
};

init();
