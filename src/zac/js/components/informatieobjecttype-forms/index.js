import React from "react";
import ReactDOM from "react-dom";

import {jsonScriptToVar} from "../../utils/json-script";

import InformatieobjectTypePermissions from './InformatieobjectTypePermissions';


const mount = () => {
    const informatieobjecttype_nodes = document.getElementsByClassName("informatieobjecttype-permissions");
    if (!informatieobjecttype_nodes.length) return;

    for (const informatieobjecttype_node of informatieobjecttype_nodes) {
        const props = {
            configuration: {
                prefix: informatieobjecttype_node.dataset.prefix,
                initial: window.parseInt(informatieobjecttype_node.dataset.initial, 10),
                extra: window.parseInt(informatieobjecttype_node.dataset.extra, 10),
                minNum: window.parseInt(informatieobjecttype_node.dataset.minNum, 10),
                maxNum: window.parseInt(informatieobjecttype_node.dataset.maxNum, 10),
            },
            catalogChoices: jsonScriptToVar(informatieobjecttype_node.dataset.catalogChoices),
            existingFormData: jsonScriptToVar(informatieobjecttype_node.dataset.existingFormData)
        };

        ReactDOM.render(<InformatieobjectTypePermissions {...props} />, informatieobjecttype_node);
    }
};

mount();
