import React, { useState } from 'react';
import PropTypes from 'prop-types';

import { Select } from '../forms/Select';


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


const AlfrescoBrowser = ({ username, password, zaaktype, bronorganisatie }) => {
    const [mode, setMode] = useState('browse');

    return (
        <React.Fragment>

            <div style={{maxWidth: '50%'}}>
                <ModeSelection selectedMode={mode} onChange={ event => setMode(event.target.value) } />
            </div>

            <contezza-documentlist
                username={username}
                password={password}
                mode={mode}
                rootfolder="-root-"
                zaaktypeurl={zaaktype}
                bronorganisatie={bronorganisatie}
            />
        </React.Fragment>
    );
};

AlfrescoBrowser.propTypes = {
    username: PropTypes.string.isRequired,  // username of the Alfresco API # TODO - use different auth
    password: PropTypes.string.isRequired,  // username of the Alfresco API # TODO - use different auth
    zaaktype: PropTypes.string.isRequired,  // URL of the zaaktype
    bronorganisatie: PropTypes.string.isRequired,  // RSIN of the bronorganisatie to use for EIO in the API
};


export { AlfrescoBrowser };
