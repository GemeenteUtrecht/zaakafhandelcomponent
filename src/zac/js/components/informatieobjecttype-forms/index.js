import React from "react";
import ReactDOM from "react-dom";
import { InformatieobjecttypePermissionForm, InformatieobjecttypeForm } from "./informatieobjecttype-form";
import {jsonScriptToVar} from "../../utils/json-script";


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
            renderForm: InformatieobjecttypePermissionForm,
            catalogChoices: jsonScriptToVar(informatieobjecttype_node.dataset.catalogChoices),
        };

        ReactDOM.render(<InformatieobjecttypeForm {...props} />, informatieobjecttype_node);
    }
};

mount();
