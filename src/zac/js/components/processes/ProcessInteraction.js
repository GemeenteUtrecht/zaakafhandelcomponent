import React, { useState } from 'react';
import PropTypes from 'prop-types';

import { useAsync } from 'react-use';

import { apiCall } from '../../utils/fetch';
import { TabList, TabContent } from '../Tabs';
import { MessageContext } from './context';
import { ProcessMessages } from './ProcessMessages';
import { Assignee, UserTask } from './UserTasks';

const UserTaskType = PropTypes.shape({
    id: PropTypes.string.isRequired,
    executeUrl: PropTypes.string.isRequired,
    name: PropTypes.string.isRequired,
    created: PropTypes.string.isRequired,
    hasForm: PropTypes.bool.isRequired,
    assignee: Assignee,
});

const ProcessInstance = PropTypes.shape({
    id: PropTypes.string.isRequired,
    definitionId: PropTypes.string.isRequired,
    title: PropTypes.string.isRequired,
    subProcesses: PropTypes.array,
    messages: PropTypes.array,
    userTasks: PropTypes.arrayOf(UserTaskType),
});


const UserTaskList = ({ zaakUrl, userTasks }) => {
    return (
        <React.Fragment>
            { userTasks.map( (userTask) => (
                <UserTask
                    key={userTask.id}
                    zaakUrl={zaakUrl}
                    taskId={userTask.id}
                    taskUrl={userTask.executeUrl}
                    name={userTask.name}
                    created={userTask.created}
                    assignee={userTask.assignee}
                    hasForm={userTask.hasForm}
                />
            ) ) }
        </React.Fragment>
    );
};

UserTaskList.propTypes = {
    zaakUrl: PropTypes.string.isRequired,
    userTasks: PropTypes.arrayOf(UserTaskType),
};


const SubProcessUserTaskList = ({ zaakUrl, processInstance, parentTitles=[] }) => {
    const breadcrumbs = [...parentTitles, processInstance.title];
    return (
        <React.Fragment>
            { processInstance.userTasks.length ?
                <div className="user-tasks__subprocess">{ breadcrumbs.join(' > ') } </div>
                : null
            }
            <UserTaskList zaakUrl={zaakUrl} userTasks={processInstance.userTasks} />
            {
                processInstance.subProcesses.map( (subProcess) => (
                    <SubProcessUserTaskList
                        key={subProcess.id}
                        zaakUrl={zaakUrl}
                        processInstance={subProcess}
                        parentTitles={breadcrumbs}
                    />
                ) )
            }
        </React.Fragment>
    );
};

SubProcessUserTaskList.propTypes = {
    zaakUrl: PropTypes.string.isRequired,
    processInstance: ProcessInstance.isRequired,
    parentTitles: PropTypes.arrayOf(PropTypes.string),
};


const UserTasksPanel = ({ numChildren, title, modifier='primary', children }) => {
    if (!numChildren) return null;
    return (
        <div className={`user-tasks__task-list user-tasks__task-list--${modifier}`}>
            <h2 className="user-tasks__title">{title}</h2>
            {children}
        </div>
    );
};

UserTasksPanel.propTypes = {
    numChildren: PropTypes.number.isRequired,
    title: PropTypes.string.isRequired,
    modifier: PropTypes.string,
    children: PropTypes.node,
};


const ProcessInteraction = ({zaak, endpoint, sendMessageUrl, canDoUsertasks=false, canSendBpmnMessages=false}) => {

    const state = useAsync(async () => {
        const response = await apiCall(endpoint);
        const processInstances = await response.json();
        return processInstances;
    }, [endpoint]);

    if (state.loading) {
        return (<span className="loader"></span>);
    }

    const getMessageContext = (instanceId) => {
        return {
            processInstanceId: instanceId,
            hasPermission: canSendBpmnMessages,
            sendMessageUrl,
        };
    }

    return (
        <TabList>
            {
                state.value.map( (processInstance) => (
                    <TabContent key={processInstance.id} title={processInstance.title}>

                        <MessageContext.Provider value={ getMessageContext(processInstance.id) }>
                            <ProcessMessages messages={processInstance.messages} />
                        </MessageContext.Provider>

                        { !canDoUsertasks ? null : (
                            <div className="user-tasks">

                                <UserTasksPanel numChildren={processInstance.userTasks.length} title="Taken" modifier="primary">
                                    <UserTaskList zaakUrl={zaak} userTasks={processInstance.userTasks} />
                                </UserTasksPanel>

                                <UserTasksPanel numChildren={processInstance.subProcesses.length} title="Deeltaken" modifier="nested">
                                    { processInstance.subProcesses.map( (subProcess) => (
                                        <SubProcessUserTaskList key={subProcess.id} zaakUrl={zaak} processInstance={subProcess} />
                                    ) ) }
                                </UserTasksPanel>

                            </div>
                        ) }

                    </TabContent>
                ) )
            }
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
