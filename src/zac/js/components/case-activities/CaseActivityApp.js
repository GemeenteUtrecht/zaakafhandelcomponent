import React, { useState } from 'react';
import PropTypes from 'prop-types';

import { AddActivityButton } from './AddActivityButton';
import { AddActvityModal } from './AddActivityModal';
import { CaseActivityList } from './CaseActivityList';
import { EventsContext } from './context';


const CaseActivityApp = ({ zaak, endpoint, eventsEndpoint, controlsNode }) => {
    const [isAdding, setIsAdding] = useState(false);
    const [lastActivityId, setLastActivityId] = useState(null);
    const [lastEventId, setLastEventId] = useState(null);

    const eventsContext = {
        endpoint: eventsEndpoint,
        onCreate: (event) => setLastEventId(event.id)
    };

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

            <EventsContext.Provider value={eventsContext}>
                <CaseActivityList
                    zaak={zaak}
                    endpoint={endpoint}
                    eventsEndpoint={eventsEndpoint}
                    lastActivityId={lastActivityId}
                    lastEventId={lastEventId}
                />
            </EventsContext.Provider>
        </React.Fragment>
    );
};

CaseActivityApp.propTypes = {
    zaak: PropTypes.string.isRequired,
    endpoint: PropTypes.string.isRequired,
    eventsEndpoint: PropTypes.string.isRequired,
    controlsNode: PropTypes.object.isRequired,
};


export { CaseActivityApp };
