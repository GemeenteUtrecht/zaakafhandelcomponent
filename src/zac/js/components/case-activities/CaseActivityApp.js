import React, { useState } from 'react';
import PropTypes from 'prop-types';

import { AddActivityButton } from './AddActivityButton';
import { AddActvityModal } from './AddActivityModal';
import { CaseActivityList } from './CaseActivityList';


const CaseActivityApp = ({ zaak, endpoint, controlsNode }) => {
    const [isAdding, setIsAdding] = useState(false);
    return (
        <React.Fragment>
            <AddActivityButton portalNode={controlsNode} onClick={ () => setIsAdding(true) } />
            <AddActvityModal
                endpoint={endpoint}
                isOpen={isAdding}
                closeModal={ () => setIsAdding(false) }
            />
            <CaseActivityList zaak={zaak} endpoint={endpoint} />
        </React.Fragment>
    );
};

CaseActivityApp.propTypes = {
    zaak: PropTypes.string.isRequired,
    endpoint: PropTypes.string.isRequired,
    controlsNode: PropTypes.object.isRequired,
};


export { CaseActivityApp };
