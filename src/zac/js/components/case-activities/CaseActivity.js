import React from 'react';
import PropTypes from 'prop-types';

import { timeSince } from '../../utils/time-since';
import { EventType, EventTimeline } from './Event';
import { CaseActivityActions } from './CaseActivityActions';
import { CaseActivityAssignee } from './CaseActivityAssignee';
import { Activity } from './types';


const CaseActivity = ({ activity }) => {
    const isOnGoing = activity.status === 'on_going';
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
                    <CaseActivityAssignee
                        activityUrl={ activity.url }
                        canSet={ isOnGoing }
                        userId={activity.assignee}
                    />
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
