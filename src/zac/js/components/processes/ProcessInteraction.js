import React from 'react';
import PropTypes from 'prop-types';

import { TabList, TabContent } from '../Tabs';
import { MessageContext } from './context';
import { ProcessMessages } from './ProcessMessages';


const ProcessInteraction = ({zaak, endpoint, sendMessageUrl, canDoUserTasks=false, canSendBpmnMessages=false}) => {

    const getMessageContext = (instanceId) => {
        return {
            processInstanceId: instanceId,
            hasPermission: canSendBpmnMessages,
            sendMessageUrl,
        };
    }

    return (
        <TabList>

            <TabContent title="Proces 1">

                <MessageContext.Provider value={ getMessageContext('proces:1') }>
                    <ProcessMessages messages={['Annuleer behandeling', 'Advies vragen']} />
                </MessageContext.Provider>

            </TabContent>

            <TabContent title="Proces 2">

                <MessageContext.Provider value={ getMessageContext('proces:2') }>
                    <ProcessMessages messages={['Dummy message']} />
                </MessageContext.Provider>

            </TabContent>

        </TabList>
    );
};


ProcessInteraction.propTypes = {
    zaak: PropTypes.string.isRequired,
    endpoint: PropTypes.string.isRequired,
    sendMessageUrl: PropTypes.string.isRequired,
    canDoUserTasks: PropTypes.bool,
    canSendBpmnMessages: PropTypes.bool,
};


export { ProcessInteraction };
