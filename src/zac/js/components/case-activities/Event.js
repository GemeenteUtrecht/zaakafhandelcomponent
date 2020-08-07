import React from 'react';
import PropTypes from 'prop-types';

import { timeSince } from '../../utils/time-since';
import { Timeline, ListItem } from '../timeline';
import { AddNotes } from './AddNotes';
import { EventType } from './types';


const EventTimeline = ({ activityId, onGoing, children }) => {
    return (
        <React.Fragment>
            <Timeline>

                { children.map( (event) => (
                    <ListItem
                        key={event.id}
                        time={timeSince(event.created)}
                        exactTime={event.created}
                        headingLevel={2}>
                        {event.notes}
                    </ListItem>
                ) ) }

            </Timeline>

            { onGoing ? <AddNotes activityId={activityId} /> : null }
        </React.Fragment>
    );
};

EventTimeline.propTypes = {
    activityId: PropTypes.number.isRequired,
    onGoing: PropTypes.bool.isRequired,
    children: PropTypes.arrayOf(EventType).isRequired,
};


export { EventType, EventTimeline };
