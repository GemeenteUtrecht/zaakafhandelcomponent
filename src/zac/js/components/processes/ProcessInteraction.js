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
                        <div className="user-tasks">
                            <div className="user-tasks__task-list user-tasks__task-list--primary">
                                <h2 className="user-tasks__title">Taken</h2>

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

                            <div className="user-tasks__task-list user-tasks__task-list--nested">
                                <h2 className="user-tasks__title">Deeltaken</h2>

                                <div className="user-tasks__subprocess"> Sub 1 </div>

                                <UserTask
                                    zaakUrl={zaak}
                                    taskId="proces:3:task:1"
                                    taskUrl="/core/zaken/:org/:identificatie/proces:3:task:1"
                                    name="Adviseren"
                                    created="2020-07-30T15:03:21Z"
                                    assignee={{username: 'johndoe', firstName: '', lastName: ''}}
                                    hasForm={true}
                                />

                                <div className="user-tasks__subprocess"> Sub 2 &gt; Sub 3 </div>

                                <UserTask
                                    zaakUrl={zaak}
                                    taskId="proces:4:task:1"
                                    taskUrl="/core/zaken/:org/:identificatie/proces:4:task:1"
                                    name="Beoordelen"
                                    created="2020-07-30T15:03:21Z"
                                    assignee={{username: 'johndoe', firstName: '', lastName: ''}}
                                    hasForm={true}
                                />

                                <UserTask
                                    zaakUrl={zaak}
                                    taskId="proces:4:task:2"
                                    taskUrl="/core/zaken/:org/:identificatie/proces:4:task:2"
                                    name="Debugging"
                                    created="2020-07-30T15:03:21Z"
                                    hasForm={true}
                                />

                            </div>
                        </div>
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
