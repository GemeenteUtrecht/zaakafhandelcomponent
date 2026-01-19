import React from 'react';
import ReactDOM from 'react-dom';

import { AlfrescoDocumentSelection } from './AlfrescoDocumentSelection';

const SELECTOR = '.alfresco-document-selection';

const nodes = document.querySelectorAll(SELECTOR);

for (const node of nodes) {
    const props = node.dataset;
    ReactDOM.render(<AlfrescoDocumentSelection {...props} />, node);
}
