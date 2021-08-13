import { JSONEditor } from '@json-editor/json-editor';
import { jsonScriptToVar } from "../../utils/json-script";


const displayPolicy = (editor_node, role_node, policy_node) => {
    const jsonSchemas = jsonScriptToVar("jsonSchemas");

    const displayJsonEditor = (object_type) => {
        const schema = jsonSchemas[object_type] || {};
        schema.title = "Blueprint data";
        const jsonEditor = new JSONEditor(
            editor_node,
            {"schema": schema, "no_additional_properties": true}
        );

        if (policy_node.value) {
            const json = JSON.parse(policy_node.value);
            jsonEditor.setValue(json);
        }

        jsonEditor.on('change', function() {
            const errors = jsonEditor.validate();
            if (errors.length) {
                console.log(errors);
            }
            else {
                const json = jsonEditor.getValue();
                policy_node.value = JSON.stringify(json);
            }
        });

        return jsonEditor;
    };

    let editor = displayJsonEditor(role_node.value);

    role_node.addEventListener('change', function() {
        console.log("change role node");
        editor.destroy();
        editor = displayJsonEditor(role_node.value);
    });

};


// initialize
const editor_node = document.getElementById("policy_editor");
const role_node = document.getElementById("id_role");
const policy_node = document.getElementById("id_policy");

if (editor_node) {
    displayPolicy(editor_node, role_node, policy_node);
}
