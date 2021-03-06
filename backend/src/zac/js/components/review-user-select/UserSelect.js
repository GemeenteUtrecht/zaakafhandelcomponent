import React, { useContext, useEffect, useState } from 'react';
import PropTypes from 'prop-types';

import AsyncSelect from 'react-select/async';

import { fetchUsers } from '../../utils/users';
import { HiddenCheckbox, DatePickerInput } from '../forms/Inputs';
import DeleteButton from '../forms/DeleteButton';
import { ErrorList, Wrapper } from '../forms/Utils';
import { TitleContext } from '../forms/context';

const ENDPOINT = '/api/accounts/users';

const getUsers = (inputValue) => {
    const selectedUserInputs = Array.from(document.getElementsByClassName('input--kownsl_user'));
    const excludedUsers = selectedUserInputs.map((element) => ({ exclude: element.id }));

    return fetchUsers({ inputValue, ENDPOINT, excludedUsers });
};

const isEmpty = (obj) => {
    if (!obj) {
        return true;
    }
    return Object.keys(obj).length === 0;
};

const extractErrors = (errList) => errList.map((err) => err.msg);

const UserSelect = ({
    index, totalStepsIndex, data: { errors }, onDelete,
}) => {
    const [selectedData, setSelectedData] = useState(null);
    const [hiddenInputs, setHiddenInputs] = useState(null);

    // Create hidden inputs of the selected users
    const getHiddenInputs = (selectedUsers) => {
        const inputs = selectedUsers
            ? selectedUsers.map((user) => (
                <HiddenCheckbox
                    name="kownsl_users"
                    value={user.value}
                    key={user.value}
                    className="input input--hidden input--kownsl_user"
                    id={user.userObject.username}
                    checked
                    required
                />
            ))
            : <HiddenCheckbox name="kownsl_users" checked={false} required />;
        setHiddenInputs(inputs);
    };

    useEffect(() => {
        getHiddenInputs(selectedData);
    }, [selectedData]);

    const title = useContext(TitleContext);
    const placeholder = title ? `Selecteer ${title.toLowerCase()}` : null;

    return (
        <div className="user-select detail-card">
            { (errors && !isEmpty(errors.__all__))
                ? (
                    <Wrapper errors={errors.__all__}>
                        <ErrorList errors={extractErrors(errors.__all__)} />
                    </Wrapper>
                ) : null}

            { (totalStepsIndex !== 0) && (
                <div className="user-select__title">
                    <h3>{`Stap ${index + 1}`}</h3>

                    { (index === totalStepsIndex && index !== 0)
                    && <DeleteButton onDelete={onDelete} /> }
                </div>
            )}
            <div className="user-select__selector">
                {hiddenInputs}
                <AsyncSelect
                    isMulti
                    placeholder={placeholder}
                    name={`kownsl_users${-index}`}
                    defaultOptions={false}
                    loadOptions={getUsers}
                    onChange={(value) => setSelectedData(value)}
                />
            </div>
            <DatePickerInput
                name="deadline"
                label="Uiterste datum:"
                minDate={new Date()}
                required
            />
        </div>
    );
};

UserSelect.propTypes = {
    index: PropTypes.number.isRequired,
    totalStepsIndex: PropTypes.number,
    data: PropTypes.objectOf(PropTypes.object).isRequired,
    onDelete: PropTypes.func,
};

export default UserSelect;
