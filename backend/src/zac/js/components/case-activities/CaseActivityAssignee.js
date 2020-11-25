import React, { useContext } from 'react';
import PropTypes from 'prop-types';

import { useAsync } from 'react-use';

import { get, patch } from '../../utils/fetch';
import { getUserName } from '../../utils/users';
import { CsrfTokenContext } from '../forms/context';
import { UserSelection } from '../user-selection';
import { ActivitiesContext } from './context';


const USER_CACHE = {};

const getAssignee = async (userId) => {
    if (userId == null) {
        return null;
    }

    if (USER_CACHE[userId]) {
        return USER_CACHE[userId];
    }

    const user = await get(`/accounts/api/users/${userId}`);
    return user;
};


const setAssignee = async (activityUrl, csrftoken, user) => {
    const userId = (user == null) ? null : user.id;
    const response = await patch(activityUrl, csrftoken, {assignee: userId});
    if (!response.ok) {
        console.error(response.data);
    }
};


const CaseActivityAssignee = ({ activityUrl, canSet, userId=null }) => {
    const activitiesContext = useContext(ActivitiesContext);
    const csrftoken = useContext(CsrfTokenContext);

    const { loading, value } = useAsync(
        async () => getAssignee(userId),
        [userId]
    );

    const onUserSelection = async (user) => {
        await setAssignee(activityUrl, csrftoken, user);
        activitiesContext.refresh();
    }

    if (loading || value == null) {
        return (
            <React.Fragment>
                {
                    (!loading && canSet) ?
                        <UserSelection
                            btnLabel="Selecteer verantwoordelijke"
                            onSelection={ onUserSelection }
                            asLink
                        />
                        : <span className="soft-info soft-info--normal-size">Geen verantwoordelijke bepaald.</span>

                }
            </React.Fragment>
        );
    }

    // at this point, we are sure the async call is not loading anymore, and userId is
    // an actual ID, so we have a name
    return (
        <React.Fragment>
            {'Verantwoordelijke: '}
            <strong>
                {getUserName(value)}
            </strong>
            {
                canSet ? (
                    <div>
                        <UserSelection btnLabel="wijzig" onSelection={ onUserSelection } asLink />
                    </div>
                ) : null
            }
        </React.Fragment>
    );
};

CaseActivityAssignee.propTypes = {
    activityUrl: PropTypes.string.isRequired,
    canSet: PropTypes.bool.isRequired,
    userId: PropTypes.number,
};


export { CaseActivityAssignee };
