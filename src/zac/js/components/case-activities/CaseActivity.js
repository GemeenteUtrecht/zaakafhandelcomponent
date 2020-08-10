import React, { useContext } from 'react';
import PropTypes from 'prop-types';

import { patch } from '../../utils/fetch';
import { timeSince } from '../../utils/time-since';
import { CsrfTokenContext } from '../forms/context';
import { UserSelection } from '../user-selection';

import { ActivitiesContext } from './context';
import { EventType, EventTimeline } from './Event';
import { CaseActivityActions } from './CaseActivityActions';
import { Activity } from './types';


const setAssignee = async (activity, csrftoken, user) => {
    const userId = (user == null) ? null : user.id;
    const response = await patch(activity.url, csrftoken, {assignee: userId});
    if (!response.ok) {
        console.error(response.data);
    }
};


const CaseActivity = ({ activity }) => {
    const isOnGoing = activity.status === 'on_going';
    const activitiesContext = useContext(ActivitiesContext);
    const csrftoken = useContext(CsrfTokenContext);

    const onUserSelection = async (user) => {
        await setAssignee(activity, csrftoken, user);
        activitiesContext.refresh();
    }

    return (
        <article className="case-activity">

            <header className="case-activity__meta">
                <div className="case-activity__id">
                    <div className="case-activity__name">
                        {activity.name}
                    </div>

                    <time className="case-activity__timestamp" title={activity.created}>
                        {timeSince(activity.created)}
                    </time>
                </div>

                <CaseActivityActions activity={activity} />

                <div className="case-activity__assignee">
                    {'Verantwoordelijke: '}
                    {
                        activity.assignee ?? (
                            isOnGoing ?
                                <UserSelection btnLabel="Selecteer" onSelection={ onUserSelection } />
                                : <span className="soft-info soft-info--normal-size">-</span>
                        )
                    }
                </div>

                <div className="case-activity__document">
                    {
                        activity.document ? (
                            <a className="btn btn--small" onClick={() => alert('todo')}>
                                Toon documentinformatie
                            </a>
                        )
                        : <span className="soft-info soft-info--normal-size">Document ontbreekt.</span>
                    }
                </div>

            </header>

            <section className="case-activity__content">
                {activity.remarks}
            </section>

            <section className="case-activity__timeline">
                <EventTimeline activityId={activity.id} onGoing={isOnGoing}>
                    {activity.events}
                </EventTimeline>
            </section>

        </article>
    );
};


CaseActivity.propTypes = {
    activity: Activity.isRequired,
};


export { Activity, CaseActivity };
