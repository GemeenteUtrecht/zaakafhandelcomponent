import React from 'react';
import PropTypes from 'prop-types';

import { timeSince } from '../../utils/time-since';
import { Timeline, ListItem } from '../timeline';


const EventType = PropTypes.shape({
    id: PropTypes.number.isRequired,
    activity: PropTypes.number.isRequired,
    notes: PropTypes.string.isRequired,
    created: PropTypes.string.isRequired,
});


const EventTimeline = ({ children }) => {
    return (
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
    );
};

EventTimeline.propTypes = {
    children: PropTypes.arrayOf(EventType).isRequired,
};

export { EventType, EventTimeline };
