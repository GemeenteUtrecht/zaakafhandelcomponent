import React from 'react';

const MessageContext = React.createContext({
    processInstanceId: '',
    sendMessageUrl: '',
    hasPermission: false,
});

export { MessageContext };
