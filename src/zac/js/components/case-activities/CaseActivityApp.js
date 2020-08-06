import React, { useState } from 'react';
import PropTypes from 'prop-types';

import { AddActivityButton } from './AddActivityButton';
import { AddActvityModal } from './AddActivityModal';
import { CaseActivityList } from './CaseActivityList';


const CaseActivityApp = ({ zaak, endpoint, controlsNode }) => {
    const [isAdding, setIsAdding] = useState(false);
    const [lastActivityId, setLastActivityId] = useState(null);

    return (
        <React.Fragment>
            <AddActivityButton portalNode={controlsNode} onClick={ () => setIsAdding(true) } />
            <AddActvityModal
                endpoint={endpoint}
                zaak={zaak}
                isOpen={isAdding}
                closeModal={ () => setIsAdding(false) }
                setLastActivityId={setLastActivityId}
            />
            <CaseActivityList zaak={zaak} endpoint={endpoint} lastActivityId={lastActivityId} />
        </React.Fragment>
    );
};

CaseActivityApp.propTypes = {
    zaak: PropTypes.string.isRequired,
    endpoint: PropTypes.string.isRequired,
    controlsNode: PropTypes.object.isRequired,
};


export { CaseActivityApp };
