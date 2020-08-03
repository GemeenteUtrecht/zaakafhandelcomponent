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

const UserTaskContext = React.createContext({
    claimTaskUrl: '',
});

export { MessageContext, CurrentUserContext, UserTaskContext };
