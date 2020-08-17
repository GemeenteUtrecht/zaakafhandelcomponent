import React from 'react';


const EventsContext = React.createContext({
    endpoint: '',
    onCreate: () => {},
});


const ActivitiesContext = React.createContext({
    refresh: () => { console.log('refresh requested') },
    canMutate: false,
});


export { EventsContext, ActivitiesContext };
