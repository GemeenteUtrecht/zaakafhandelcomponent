import React, { useRef, useEffect } from 'react';
import PropTypes from 'prop-types';

import { useImmerReducer } from "use-immer";

import { Select } from '../forms/Select';
import { TextInput, PasswordInput } from '../forms/Inputs';


const initialState = {
    mode: "browse",
    username: "",
    password: "",
    loadDocumentList: false,
};


const reducer = (draft, action) => {
    switch (action.type) {
        case "FIELD_CHANGED": {
            const { name, value } = action.payload;
            draft[name] = value;
            if ( !(draft.username && draft.password) ) {
                draft.loadDocumentList = false;
            }
            break;
        }
        case "ALFRESCO_LOGIN": {
            if (draft.username && draft.password) {
                draft.loadDocumentList = true;
            }
            break;
        }
        default:
            break;
    }
}


const ModeSelection = ({ onChange, selectedMode="browse" }) => {
    return (
        <Select
            name="mode"
            label="Zoekmodus"
            value={selectedMode}
            choices={[
                ["browse", "Bladeren"],
                ["search", "Zoeken"],
            ]}
            onChange={onChange}
        />
    );
};


const AlfrescoBrowser = ({ zaaktype, bronorganisatie, onEIOCreated }) => {
    const docList = useRef(null);

    const [state, dispatch] = useImmerReducer(reducer, initialState);
    const { mode, username, password, loadDocumentList } = state;

    const onFieldChange = (event) => {
        const { name, value } = event.target;
        dispatch({
            type: "FIELD_CHANGED",
            payload: {
                name,
                value
            }
        });
    };

    const onLogin = (event) => {
        dispatch({
            type: "ALFRESCO_LOGIN",
        });
        event.preventDefault();
    };

    const callbackUrlHandler = (event) => {
        onEIOCreated(event.detail);
    };

    // note that the docList.current can't be included in the conditionals - at the time
    // of first-time render of the webcomponent, the value is still null, which means that
    // there will be no subscription to the callbackurl event.
    useEffect(
        () => {
            if (!docList.current) return;
            docList.current.addEventListener("callbackurl", callbackUrlHandler);
            return () => {
                docList.current.removeEventListener("callbackurl", callbackUrlHandler);
            };
        }
    );

    return (
        <>
            <form className="form form--modal" autoComplete="off" onSubmit={onLogin}>
                <div className="form__field-group">
                    <TextInput
                        name="username"
                        label="Gebruikersnaam"
                        helpText="Alfresco gebruikersnaam"
                        value={username}
                        onChange={onFieldChange}
                        required
                    />
                    <PasswordInput
                        name="password"
                        label="Wachtwoord"
                        helpText="Alfresco wachtwoord"
                        value={password}
                        onChange={onFieldChange}
                        required
                    />
                    <div className="input" style={{ display: 'flex', alignItems: 'flex-end' }}>
                        <button type="submit" className="btn btn--default">Inloggen</button>
                    </div>
                </div>
                <ModeSelection selectedMode={mode} onChange={onFieldChange} />
            </form>
            {
                !loadDocumentList ? (
                    <div className="permission-check permission-check--failed">
                        Geef een gebruikersnaam en wachtwoord op om op Alfresco in te loggen.
                    </div>
                ) : (
                    <contezza-documentlist
                        ref={docList}
                        username={username}
                        password={password}
                        mode={mode}
                        rootfolder="-root-"
                        zaaktypeurl={zaaktype}
                        bronorganisatie={bronorganisatie}
                    />
                )
            }
        </>
    );
};

AlfrescoBrowser.propTypes = {
    zaaktype: PropTypes.string.isRequired,  // URL of the zaaktype
    bronorganisatie: PropTypes.string.isRequired,  // RSIN of the bronorganisatie to use for EIO in the API
    onEIOCreated: PropTypes.func.isRequired,  // callback receiving the EIO url
};


export { AlfrescoBrowser };
