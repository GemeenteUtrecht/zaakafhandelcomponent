import React, { useContext } from 'react';
import PropTypes from 'prop-types';

import { CsrfInput } from '../forms/csrf';
import { MessageContext } from './context';


const MessageForm = ({ name }) => {

    const messageContext = useContext(MessageContext);

    return (
        <form action={messageContext.sendMessageUrl} method="post" className="form process-messages__form">
            <CsrfInput />
            <input type="hidden" name="process_instance_id" defaultValue={messageContext.processInstanceId} />
            <button
                className="btn btn--small"
                name="message"
                value={name}
                disabled={!messageContext.hasPermission}
            > {name} </button>
        </form>
    );
};

MessageForm.propTypes = {
    name: PropTypes.string.isRequired,
};


const ProcessMessages = ({ messages=[] }) => {
    if (!messages.length) return null;

    return (
        <div className="process-messages">
            <label className="process-messages__intro">Acties:</label>
            { messages.map( (message) => <MessageForm key={message} name={message} /> ) }
        </div>
    );
};

ProcessMessages.propTypes = {
    messages: PropTypes.arrayOf(PropTypes.string.isRequired),
};

export { ProcessMessages };
