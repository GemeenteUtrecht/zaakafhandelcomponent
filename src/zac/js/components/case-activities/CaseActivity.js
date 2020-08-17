import React, { useContext } from 'react';
import PropTypes from 'prop-types';

import { timeSince } from '../../utils/time-since';
import { EventType, EventTimeline } from './Event';
import { CaseActivityActions } from './CaseActivityActions';
import { CaseActivityAssignee } from './CaseActivityAssignee';
import { CaseActivityDocument } from './CaseActivityDocument';
import { ActivitiesContext } from './context';
import { Activity } from './types';


const CaseActivity = ({ activity }) => {
    const isOnGoing = activity.status === 'on_going';
    const activitiesContext = useContext(ActivitiesContext);

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

                { activitiesContext.canMutate ? <CaseActivityActions activity={activity} /> : null }

                <div className="case-activity__assignee">
                    <CaseActivityAssignee
                        activityUrl={ activity.url }
                        canSet={ isOnGoing && activitiesContext.canMutate }
                        userId={activity.assignee}
                    />
                </div>

                <div className="case-activity__document">
                    <CaseActivityDocument canMutate={ isOnGoing && activitiesContext.canMutate } activity={activity} />
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
