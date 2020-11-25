import React from 'react';
import ReactDOM from 'react-dom';

import { TitleContext } from '../forms/context';
import { FormSet } from '../formsets/FormSet';
import UserSelect from './UserSelect';
import AddStep from './AddStep';

const NODE_ID = 'react-review-users';

const init = () => {
    const node = document.getElementById(NODE_ID);

    if (!node) return;

    const props = {
        configuration: {
            prefix: node.dataset.prefix,
            suffix: node.dataset.suffix,
            initial: window.parseInt(node.dataset.initial, 10),
            extra: 0,
            minNum: window.parseInt(node.dataset.minNum, 10),
            maxNum: window.parseInt(node.dataset.maxNum, 10),
        },
        renderForm: UserSelect,
        renderAdd: AddStep,
        formData: [{}],
    };
    ReactDOM.render(
        <TitleContext.Provider value={node.dataset.title}>
            <FormSet {...props} />
        </TitleContext.Provider>,
        node,
    );
};

init();
