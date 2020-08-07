import PropTypes from 'prop-types';

const EventType = PropTypes.shape({
    id: PropTypes.number.isRequired,
    // url: PropTypes.string.isRequired,
    activity: PropTypes.number.isRequired,
    notes: PropTypes.string.isRequired,
    created: PropTypes.string.isRequired,
});

const Activity = PropTypes.shape({
    id: PropTypes.number.isRequired,
    url: PropTypes.string.isRequired,
    zaak: PropTypes.string.isRequired,
    name: PropTypes.string.isRequired,
    remarks: PropTypes.string.isRequired,
    status: PropTypes.oneOf(['on_going', 'finished']),
    created: PropTypes.string.isRequired,
    assignee: PropTypes.number,
    document: PropTypes.string,
    events: PropTypes.arrayOf(EventType),
});


export { Activity, EventType };
