import React from 'react';
import PropTypes from 'prop-types';
import { useAsync } from 'react-use';

import { apiCall } from '../../utils/fetch';
import { timeSince } from '../../utils/time-since';
import { TabList, TabContent } from '../Tabs';


const ActivityList = ({ children }) => {
    return (
        <ul>
            { children.map( activity => (
                <li key={activity.id}>
                    { activity.name }
                    <br />
                    ({ timeSince(activity.created) })
                </li>
            ) ) }
        </ul>
    );
};

ActivityList.propTypes = {
    children: PropTypes.arrayOf(
        PropTypes.shape({
            id: PropTypes.number.isRequired,
            zaak: PropTypes.string.isRequired,
            name: PropTypes.string.isRequired,
            remarks: PropTypes.string.isRequired,
            status: PropTypes.oneOf(['on_going', 'finished']),
            created: PropTypes.string.isRequired,
            assignee: PropTypes.number,
            document: PropTypes.string,
        }),
    ),
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
