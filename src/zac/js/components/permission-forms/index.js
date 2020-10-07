import React from "react";
import ReactDOM from "react-dom";
import { InformatieobjecttypePermissionForm } from "./informatieobjecttype";
import {jsonScriptToVar} from "../../utils/json-script";


const mount = () => {
    const informatieobjecttype_nodes = document.getElementsByClassName("informatieobjecttype-permissions");
    if (!informatieobjecttype_nodes.length) return;

    for (const informatieobjecttype_node of informatieobjecttype_nodes) {
            const props = {
            configuration: {
                prefix: informatieobjecttype_node.dataset.prefix,
                initial: window.parseInt(informatieobjecttype_node.dataset.initial, 10),
                extra: 0,
                minNum: window.parseInt(informatieobjecttype_node.dataset.minNum, 10),
                maxNum: window.parseInt(informatieobjecttype_node.dataset.maxNum, 10),
            },
            initialData: jsonScriptToVar(informatieobjecttype_node.dataset.formdataElement),
            catalogData: jsonScriptToVar(informatieobjecttype_node.dataset.catalogData),
            informatieobjecttypeData: jsonScriptToVar(informatieobjecttype_node.dataset.informatieobjecttypeData)
        };

        ReactDOM.render(<InformatieobjecttypePermissionForm {...props} />, informatieobjecttype_node);
    }
};

mount();
