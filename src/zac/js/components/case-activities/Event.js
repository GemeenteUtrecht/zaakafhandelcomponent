import React, { useState, useContext } from 'react';
import PropTypes from 'prop-types';

import { CsrfTokenContext } from '../forms/context';
import { SubmitRow } from '../forms/Utils';
import { post } from '../../utils/fetch';
import { timeSince } from '../../utils/time-since';
import { Timeline, ListItem } from '../timeline';
import { EventsContext } from './context';


const EventType = PropTypes.shape({
    id: PropTypes.number.isRequired,
    activity: PropTypes.number.isRequired,
    notes: PropTypes.string.isRequired,
    created: PropTypes.string.isRequired,
});


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



const AddNotes = ({ activityId }) => {
    const [value, setValue] = useState('');
    const [focused, setFocused] = useState(false);

    const eventsContext = useContext(EventsContext);
    const csrftoken = useContext(CsrfTokenContext);

    const createEvent = async (event) => {
        event.preventDefault();
        const {ok, status, data} = await post(eventsContext.endpoint, csrftoken, {
            activity: activityId,
            notes: value,
        });

        if (!ok) {
            console.error(data);
        } else {
            eventsContext.onCreate(data);
        }
    };

    const showSubmit = focused || value;

    const firstLine = value.split('\n')[0];
    return (
        <form className="case-activity__note-form" onSubmit={createEvent}>
            <textarea
                name="notes"
                className="case-activity__add-note"
                value={focused ? value : firstLine}
                onChange={ (event) => setValue(event.target.value) }
                placeholder="Notitie toevoegen"
                onFocus={ () => setFocused(true) }
                onBlur={ () => setFocused(false) }
                required={true}
            />
            {
                showSubmit ?
                <SubmitRow text="toevoegen" btnModifier="small" />
                : null }
        </form>
    );
};

AddNotes.propTypes = {
    activityId: PropTypes.number.isRequired,
};


export { EventType, EventTimeline };
