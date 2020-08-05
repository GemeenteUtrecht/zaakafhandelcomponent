import React from 'react';
import PropTypes from 'prop-types';
import { useAsync } from 'react-use';

import { apiCall } from '../../utils/fetch';
import { timeSince } from '../../utils/time-since';
import { TabList, TabContent } from '../Tabs';
import { Activity, CaseActivity } from './CaseActivity';

const ActivityList = ({ children }) => {
    return (
        <React.Fragment>
            {
                children.map( (activity) => (<CaseActivity key={activity.id} activity={activity} />) )
            }
        </React.Fragment>
    );
};

ActivityList.propTypes = {
    children: PropTypes.arrayOf(Activity),
};


const CaseActivityList = ({ zaak, endpoint }) => {
    const state = useAsync(async () => {
        const response = await apiCall(endpoint);
        const activities = await response.json();
        return activities;
    }, [endpoint]);

    if (state.loading) {
        return (<span className="loader"></span>);
    }

    if (!state.value.length) {
        return (<div className="soft-info soft-info--normal-size">Geen ad-hoc activiteiten bekend</div>);
    }

    const onGoing = state.value.filter(activity => activity.status === 'on_going');
    const finished = state.value.filter(activity => activity.status === 'finished');

    return (
        <TabList>
            <TabContent title="Lopend">
                <ActivityList>{onGoing}</ActivityList>
            </TabContent>

            <TabContent title="Afgesloten">
                <ActivityList>{finished}</ActivityList>
            </TabContent>
        </TabList>
    );
};

CaseActivityList.propTypes = {
    zaak: PropTypes.string.isRequired,
    endpoint: PropTypes.string.isRequired,
}

export { CaseActivityList };
