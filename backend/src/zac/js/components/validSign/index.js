import React from 'react';
import ReactDOM from 'react-dom';

import Modal from 'react-modal';

import { jsonScriptToVar } from '../../utils/json-script';
import { FormSet } from '../formsets/FormSet';
import { SignerForm } from './SignerForm';
import { AddRow } from './AddRow';


const CLASS_NAME = 'react-validsign-signers';


const init = () => {
    const nodes = document.querySelectorAll(`.${CLASS_NAME}`);

    if (!nodes.length) return;

    Modal.setAppElement(nodes[0]);

    for (const node of nodes) {
        const props = {
            configuration: {
                prefix: node.dataset.prefix,
                initial: window.parseInt(node.dataset.initial, 10),
                extra: 0,
                minNum: window.parseInt(node.dataset.minNum, 10),
                maxNum: window.parseInt(node.dataset.maxNum, 10),
            },
            renderForm: SignerForm,
            renderAdd: AddRow,
            formData: jsonScriptToVar(node.dataset.formdataElement),
        };
        ReactDOM.render(<FormSet {...props} />, node);
    }
};

init();
