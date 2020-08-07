import React, { useState } from 'react';
import PropTypes from 'prop-types';

import { SubmitRow } from '../forms/Utils';
import { timeSince } from '../../utils/time-since';
import { Timeline, ListItem } from '../timeline';


const EventType = PropTypes.shape({
    id: PropTypes.number.isRequired,
    activity: PropTypes.number.isRequired,
    notes: PropTypes.string.isRequired,
    created: PropTypes.string.isRequired,
});


const EventTimeline = ({ onGoing, children }) => {
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

            { onGoing ? <AddNotes /> : null }
        </React.Fragment>
    );
};

EventTimeline.propTypes = {
    onGoing: PropTypes.bool.isRequired,
    children: PropTypes.arrayOf(EventType).isRequired,
};



const AddNotes = ({ }) => {
    const [value, setValue] = useState('');
    const [focused, setFocused] = useState(false);

    const firstLine = value.split('\n')[0];

    return (
        <form className="case-activity__note-form">
            <textarea
                name="notes"
                className="case-activity__add-note"
                value={focused ? value : firstLine}
                onChange={ (event) => setValue(event.target.value) }
                placeholder="Notitie toevoegen"
                onFocus={ () => setFocused(true) }
                onBlur={ () => setFocused(false) }
            />
            {
                focused ?
                <SubmitRow text="toevoegen" btnModifier="small" />
                : null }
        </form>
    );
};

AddNotes.propTypes = {

};


export { EventType, EventTimeline };
