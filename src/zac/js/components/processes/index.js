import React from 'react';
import ReactDOM from 'react-dom';

import camelcaseKeys from 'camelcase-keys';

import { jsonScriptToVar } from '../../utils/json-script';
import { CsrfTokenContext } from '../forms/context';
import { CurrentUserContext } from './context';
import { ProcessInteraction } from './ProcessInteraction';

const CLASS_NAME = 'process-interaction';


const init = () => {
    const nodes = document.querySelectorAll(`.${CLASS_NAME}`);

    if (!nodes.length) return;

    const currentUser = camelcaseKeys(jsonScriptToVar('currentUser'));

    for (const node of nodes) {

        const props = {
            zaak: node.dataset.zaak,
            endpoint: node.dataset.endpoint,
            // convert to actual bools
            canDoUsertasks: node.dataset.canDoUsertasks === "true",
            canSendBpmnMessages: node.dataset.canSendBpmnMessages === "true",
            sendMessageUrl: node.dataset.sendMessageUrl,
            claimTaskUrl: node.dataset.claimTaskUrl,
        };

        ReactDOM.render(
            <CurrentUserContext.Provider value={currentUser}>
                <CsrfTokenContext.Provider value={node.dataset.csrftoken} >
                    <ProcessInteraction {...props} />
                </CsrfTokenContext.Provider>
            </CurrentUserContext.Provider>,
            node
        );
    }
};

init();
