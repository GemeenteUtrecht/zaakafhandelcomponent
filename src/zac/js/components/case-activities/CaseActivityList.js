import React from 'react';
import PropTypes from 'prop-types';
import { useAsync } from 'react-use';

import { get } from '../../utils/fetch';
import { timeSince } from '../../utils/time-since';
import { TabList, TabContent } from '../Tabs';
import { Activity, CaseActivity } from './CaseActivity';


const ActivityList = ({ children }) => {
    return (
        <React.Fragment>
            {
                children.map( (activity) => (
                    <CaseActivity key={activity.id} activity={activity} />
                ) )
            }
        </React.Fragment>
    );
};

ActivityList.propTypes = {
    children: PropTypes.arrayOf(Activity),
};


const CaseActivityList = ({ zaak, endpoint, lastActivityId=null, lastEventId=null }) => {
    // lastActivityId and lastEventId are included so that data is reloaded on creation
    // of a new activity or event within an activity
    const state = useAsync(async () => {
        const activities = await get(endpoint, {zaak});
        return activities;
    }, [endpoint, lastActivityId, lastEventId]);

    if (state.error) {
        console.error(state.error);
        return null;
    }

    if (state.loading) {
        return (<span className="loader"></span>);
    }

    if (!state.value.length) {
        return (<div className="soft-info soft-info--normal-size">Geen ad-hoc activiteiten bekend</div>);
    }

    const onGoing = state.value.filter(activity => activity.status === 'on_going');
    const finished = state.value.filter(activity => activity.status === 'finished');

    return (
        <React.Fragment>
            <TabList>
                <TabContent title="Lopend">
                    <ActivityList>{onGoing}</ActivityList>
                </TabContent>

                <TabContent title="Afgesloten">
                    <ActivityList>{finished}</ActivityList>
                </TabContent>
            </TabList>
        </React.Fragment>
    );
};

CaseActivityList.propTypes = {
    zaak: PropTypes.string.isRequired,
    endpoint: PropTypes.string.isRequired,
    lastActivityId: PropTypes.number,
    lastEventId: PropTypes.number,
};

export { CaseActivityList };
