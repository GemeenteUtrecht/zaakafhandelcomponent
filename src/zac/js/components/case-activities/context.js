import React from 'react';


const EventsContext = React.createContext({
    endpoint: '',
    onCreate: () => {},
});


export { EventsContext };
