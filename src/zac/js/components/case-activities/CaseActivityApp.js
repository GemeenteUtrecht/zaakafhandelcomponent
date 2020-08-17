import React, { useState } from 'react';
import PropTypes from 'prop-types';

import { useImmerReducer } from "use-immer";

import { AddActivityButton } from './AddActivityButton';
import { AddActvityModal } from './AddActivityModal';
import { CaseActivityList } from './CaseActivityList';
import { EventsContext, ActivitiesContext } from './context';


const getRandomId = () => {
    return Math.random().toString(36).substr(2, 5);
};

const initialState = {
    refreshId: getRandomId(),
    isAdding: false,
};

const reducer = (draft, action) => {
    switch(action.type) {
        case 'REFRESH': {
            let newId = getRandomId();
            let count = 0;
            while (newId === draft.refreshId && count < 10) {
                newId = getRandomId();
                count++;
            }
            draft.refreshId = newId;
            break;
        }
        case 'TOGGLE_ADD_ACTIVITY': {
            draft.isAdding = action.payload;
            break;
        }
        default:
            console.error(`Unknown action type ${action.type}`);
            break;
    }
};


const CaseActivityApp = ({ zaak, endpoint, eventsEndpoint, controlsNode, canMutate }) => {
    const [
        { isAdding, refreshId },
        dispatch
    ] = useImmerReducer(reducer, initialState);

    const refresh = () => dispatch({ type: 'REFRESH' });

    const eventsContext = {
        endpoint: eventsEndpoint,
        onCreate: refresh,
    };
    const activitiesContext = {refresh, canMutate};

    return (
        <React.Fragment>
            {
                canMutate ? (
                    <React.Fragment>
                        <AddActivityButton
                            portalNode={controlsNode}
                            onClick={ () => dispatch({type: 'TOGGLE_ADD_ACTIVITY', payload: true}) }
                        />
                        <AddActvityModal
                            endpoint={endpoint}
                            zaak={zaak}
                            isOpen={isAdding}
                            closeModal={ () => dispatch({type: 'TOGGLE_ADD_ACTIVITY', payload: false}) }
                            refresh={ refresh }
                        />
                    </React.Fragment>
                ) : (
                    <p className="permission-check permission-check--failed">
                        Je hebt geen rechten om activiteiten aan te maken of wijzigen.
                    </p>
                )
            }

            <EventsContext.Provider value={eventsContext}>
                <ActivitiesContext.Provider value={activitiesContext}>
                    <CaseActivityList
                        zaak={zaak}
                        endpoint={endpoint}
                        refreshId={refreshId}
                    />
                </ActivitiesContext.Provider>
            </EventsContext.Provider>
        </React.Fragment>
    );
};

CaseActivityApp.propTypes = {
    zaak: PropTypes.string.isRequired,
    endpoint: PropTypes.string.isRequired,
    eventsEndpoint: PropTypes.string.isRequired,
    controlsNode: PropTypes.object.isRequired,
    canMutate: PropTypes.bool.isRequired,
};


export { CaseActivityApp };
