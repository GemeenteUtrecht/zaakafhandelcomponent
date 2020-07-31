import React from 'react';

const MessageContext = React.createContext({
    processInstanceId: '',
    sendMessageUrl: '',
    hasPermission: false,
});


const CurrentUserContext = React.createContext({
    id: null,
    username: '',
    firstName: '',
    lastName: '',
});

export { MessageContext, CurrentUserContext };
