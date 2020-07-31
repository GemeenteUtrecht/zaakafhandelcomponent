import React from 'react';
import PropTypes from 'prop-types';

import { TabList, TabContent } from '../Tabs';
import { MessageContext } from './context';
import { ProcessMessages } from './ProcessMessages';
import { UserTask } from './UserTasks';


const ProcessInteraction = ({zaak, endpoint, sendMessageUrl, canDoUsertasks=false, canSendBpmnMessages=false}) => {

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

                {
                    !canDoUsertasks ? null : (
                        <React.Fragment>
                            <div className="user-tasks user-tasks--primary">

                                <h2>Taken</h2>
                                <UserTask
                                    zaakUrl={zaak}
                                    taskId="proces:1:task:1"
                                    taskUrl="/core/zaken/:org/:identificatie/proces:1:task:1"
                                    name="Bepalen resultaat"
                                    created="2020-07-30T15:03:21Z"
                                    assignee={{username: 'sergei', firstName: 'Sergei', lastName: 'Maertens'}}
                                    hasForm={true}
                                />

                                <UserTask
                                    zaakUrl={zaak}
                                    taskId="proces:1:task:2"
                                    taskUrl="/core/zaken/:org/:identificatie/proces:1:task:2"
                                    name="Adviesvraag configureren"
                                    created="2020-07-30T18:05:59Z"
                                    hasForm={true}
                                />

                            </div>

                            <div className="user-tasks user-tasks--nested">
                                <h2>Deeltaken</h2>
                            </div>
                        </React.Fragment>
                    )
                }

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
    canDoUsertasks: PropTypes.bool,
    canSendBpmnMessages: PropTypes.bool,
};


export { ProcessInteraction };
