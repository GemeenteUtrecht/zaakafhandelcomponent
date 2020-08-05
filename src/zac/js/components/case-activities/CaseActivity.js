import React from 'react';
import PropTypes from 'prop-types';

import { timeSince } from '../../utils/time-since';

import { EventType, EventTimeline } from './Event';


const Activity = PropTypes.shape({
    id: PropTypes.number.isRequired,
    zaak: PropTypes.string.isRequired,
    name: PropTypes.string.isRequired,
    remarks: PropTypes.string.isRequired,
    status: PropTypes.oneOf(['on_going', 'finished']),
    created: PropTypes.string.isRequired,
    assignee: PropTypes.number,
    document: PropTypes.string,
    events: PropTypes.arrayOf(EventType),
});


const CaseActivity = ({ activity }) => {
    return (
        <article className="case-activity">

            <header className="case-activity__id">
                <span className="case-activity__name">
                    {activity.name}
                </span>

                <span className="case-activity__timestamp">
                    {timeSince(activity.created)}
                </span>

                <div className="case-activity__assignee">
                    {'Verantwoordelijke: '}
                    {activity.assignee ?? <span className="soft-info">-</span>}
                </div>
            </header>

            <section className="case-activity__content">
                {activity.remarks}

                <div className="case-activity__document">
                    {
                        activity.document ? (
                            <a className="btn btn--small" onClick={() => alert('todo')}>
                                Toon documentinformatie
                            </a>
                        )
                        : <span className="soft-info">Document ontbreekt.</span>
                    }
                </div>
            </section>

            <section className="case-activity__timeline">
                <EventTimeline>{activity.events}</EventTimeline>
            </section>

        </article>
    );
};


CaseActivity.propTypes = {
    activity: Activity,
};


export { Activity, CaseActivity };
