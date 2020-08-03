import React, { useContext } from 'react';
import PropTypes from 'prop-types';

import { timeSince, timeUntil } from '../../utils/time-since';
import { CsrfInput } from '../forms/csrf';
import { CurrentUserContext } from './context';

// TODO: move to general utils!
import { getAuthorName } from '../../views/zaak-detail/utils';

const Assignee = PropTypes.shape({
    username: PropTypes.string.isRequired,
    firstName: PropTypes.string,
    lastName: PropTypes.string,
});


const ExecuteTaskBtn = ({ url }) => {
    return (<a href={url} className="btn btn--small">Uitvoeren</a> );
};

ExecuteTaskBtn.propTypes = {
    url: PropTypes.string.isRequired,
};


const TaskAssignee = ({ taskUrl, currentUserIsAssignee=false, assignee=null }) => {
    const currentUser = useContext(CurrentUserContext);
    const executeBtn = currentUserIsAssignee ?
        <ExecuteTaskBtn url={taskUrl} />
        : 'Taak is al geclaimed!'
    ;

    return (
        <React.Fragment>
            <div>{executeBtn}</div>
            <strong>{ getAuthorName(assignee) }</strong>
        </React.Fragment>
    );
};

TaskAssignee.propTypes = {
    taskUrl: PropTypes.string.isRequired,
    currentUserIsAssignee: PropTypes.bool,
    assignee: Assignee,
};


const UserTaskForm = ({ zaakUrl, taskId, taskUrl, hasForm=false }) => {
    let executeBtn = null;
    if (hasForm) {
        executeBtn = (
            <React.Fragment>
                &nbsp;of&nbsp;
                <ExecuteTaskBtn url={taskUrl} />
            </React.Fragment>
        );
    }
    return (
        <form className="user-task__claim" method="post" action="#TODO">
            <CsrfInput />
            <input type="hidden" name="task_id" value={taskId} />
            <input type="hidden" name="zaak" value={zaakUrl} />
            <button
                type="submit"
                className="btn btn--small"
                title="Claim de taak om deze uit te voeren. Je wordt hierdoor de assignee.">
                Claim
            </button>
            { executeBtn }
        </form>
    );
};

UserTaskForm.propTypes = {
    zaakUrl: PropTypes.string.isRequired,
    taskId: PropTypes.string.isRequired,
    taskUrl: PropTypes.string.isRequired,
    hasForm: PropTypes.bool,
};


const UserTask = ({ zaakUrl, taskId, taskUrl, name, created, due='', assignee=null, hasForm=false }) => {
    const currentUser = useContext(CurrentUserContext);
    const currentUserIsAssignee = assignee && assignee.username === currentUser.username;

    return (
        <div className="user-task">

            <div className="user-task__description">
                {name}
                <time className="user-task__created" title={created}>
                    {timeSince(created)} aangemaakt
                </time>
            </div>

            <div className="user-task__due">
                {
                    due ?
                        (<React.Fragment>
                            <time title={due} className="material-icons">
                                {/* TODO: use _full if due date is expired */}
                                hourglass_empty
                            </time>
                            {timeUntil(due)}
                        </React.Fragment>)
                        : null
                }
            </div>

            <div
                className="user-task__assignee"
                title={`Assignee${ currentUserIsAssignee ? ' (jij!)' : '' }`}>

                { assignee ?
                    ( <TaskAssignee taskUrl={taskUrl} currentUserIsAssignee={currentUserIsAssignee} assignee={assignee} /> )
                    : ( <UserTaskForm zaakUrl={zaakUrl} taskId={taskId} taskUrl={taskUrl} hasForm={hasForm} /> )
                }

            </div>

        </div>
    );
};

UserTask.propTypes = {
    zaakUrl: PropTypes.string.isRequired,
    taskId: PropTypes.string.isRequired,
    taskUrl: PropTypes.string.isRequired,
    name: PropTypes.string.isRequired,
    created: PropTypes.string.isRequired,
    due: PropTypes.string,
    assignee: Assignee,
    hasForm: PropTypes.bool,
};


export { Assignee, UserTask };
